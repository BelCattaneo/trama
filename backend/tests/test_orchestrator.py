from pathlib import Path

import pytest
import pytest_asyncio

from trama import db
from trama.parsing.orchestrator import _compute_confidence, _run_deterministic
from trama.parsing.schema import ParsePayload
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user

FIXTURES = Path(__file__).parent / "fixtures" / "parsing"


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest_asyncio.fixture
async def setup(node_user):
    yield node_user


# ---------- confidence formula ----------


def test_confidence_no_lines_returns_03():
    payload = ParsePayload(lines=[], warnings=[])
    assert _compute_confidence(payload) == 0.3


def test_confidence_clean_returns_10():
    payload = ParsePayload.model_validate_json(
        '{"lines":[{"product":"x","quantity":1.0}],"warnings":[]}'
    )
    assert _compute_confidence(payload) == 1.0


def test_confidence_some_warnings_returns_08():
    payload = ParsePayload.model_validate_json(
        '{"lines":[{"product":"x","quantity":1.0},{"product":"y","quantity":2.0}],'
        '"warnings":["fila 3 saltada"]}'
    )
    assert _compute_confidence(payload) == 0.8


def test_confidence_more_warnings_than_half_returns_05():
    payload = ParsePayload.model_validate_json(
        '{"lines":[{"product":"x","quantity":1.0}],'
        '"warnings":["w1","w2","w3"]}'
    )
    assert _compute_confidence(payload) == 0.5


def test_confidence_exactly_half_warnings_returns_05():
    # 1 line + 1 warning → ratio is exactly 0.5; the >= 0.5 branch wins.
    payload = ParsePayload.model_validate_json(
        '{"lines":[{"product":"x","quantity":1.0}],"warnings":["w1"]}'
    )
    assert _compute_confidence(payload) == 0.5


# ---------- _run_deterministic ----------


def test_run_deterministic_xlsx_standard_confidence_10():
    result = _run_deterministic(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        _fixture_bytes("standard.xlsx"),
    )
    assert result.strategy == "deterministic"
    assert result.confidence == 1.0
    assert result.error_message is None
    assert len(result.payload.lines) == 5


def test_run_deterministic_xlsx_malformed_returns_partial():
    result = _run_deterministic(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        _fixture_bytes("malformed.xlsx"),
    )
    assert result.strategy == "deterministic"
    assert result.payload is not None
    assert 0 < result.confidence < 1
    assert len(result.payload.warnings) > 0


def test_run_deterministic_xlsx_no_headers_returns_error():
    result = _run_deterministic(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        _fixture_bytes("no_headers.xlsx"),
    )
    assert result.confidence == 0.0
    assert result.payload is None
    assert "no se encontraron columnas reconocidas" in result.error_message


def test_run_deterministic_csv_standard_confidence_10():
    result = _run_deterministic("text/csv", _fixture_bytes("standard.csv"))
    assert result.confidence == 1.0
    assert len(result.payload.lines) == 5


# ---------- run_parse dispatch ----------


@pytest.mark.asyncio
async def test_run_parse_returns_none_for_unknown_mime(pool_lifecycle):
    from trama.parsing.orchestrator import run_parse

    assert await run_parse(None, "application/octet-stream", b"\x00") is None


# ---------- integration via /api/documents ----------


@pytest.mark.asyncio
async def test_upload_xlsx_returns_parse_attempt_confidence_10(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={
                "file": (
                    "pedido.xlsx",
                    _fixture_bytes("standard.xlsx"),
                    "application/octet-stream",
                )
            },
        )
    assert response.status_code == 201
    body = response.json()
    attempt = body["parse_attempt"]
    assert attempt is not None
    assert attempt["strategy"] == "deterministic"
    assert attempt["confidence"] == 1.0
    assert attempt["error_message"] is None
    assert len(attempt["payload"]["lines"]) == 5


@pytest.mark.asyncio
async def test_upload_xlsx_persists_parse_attempt_row(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={
                "file": (
                    "pedido.xlsx",
                    _fixture_bytes("standard.xlsx"),
                    "application/octet-stream",
                )
            },
        )
    doc_id = response.json()["document"]["id"]
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM parse_attempt WHERE document_id = %s",
                (doc_id,),
            )
            (count,) = await cur.fetchone()
    assert count == 1


@pytest.mark.asyncio
async def test_upload_csv_returns_parse_attempt(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={
                "file": (
                    "pedido.csv",
                    _fixture_bytes("standard.csv"),
                    "application/octet-stream",
                )
            },
        )
    body = response.json()
    assert body["parse_attempt"] is not None
    assert body["parse_attempt"]["confidence"] == 1.0


@pytest.mark.asyncio
async def test_upload_invalid_xlsx_persists_failed_attempt(setup):
    fake = b"PK\x03\x04" + b"xl/" + b"\x00" * 10  # passes mime detect, fails openpyxl
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("broken.xlsx", fake, "application/octet-stream")},
        )
    assert response.status_code == 201
    attempt = response.json()["parse_attempt"]
    assert attempt is not None
    assert attempt["confidence"] == 0.0
    assert attempt["error_message"]
    assert attempt["payload"] is None


# ---------- /reparse endpoint ----------


@pytest.mark.asyncio
async def test_reparse_creates_new_attempt_row(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        upload = await c.post(
            "/api/documents",
            files={
                "file": (
                    "p.xlsx",
                    _fixture_bytes("standard.xlsx"),
                    "application/octet-stream",
                )
            },
        )
        doc_id = upload.json()["document"]["id"]
        reparse = await c.post(f"/api/documents/{doc_id}/reparse")
    assert reparse.status_code == 200
    attempt = reparse.json()["parse_attempt"]
    assert attempt["strategy"] == "deterministic"
    assert attempt["confidence"] == 1.0

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM parse_attempt WHERE document_id = %s",
                (doc_id,),
            )
            (count,) = await cur.fetchone()
    assert count == 2  # original upload + reparse


@pytest.mark.asyncio
async def test_reparse_other_node_returns_404(setup):
    other = await make_node_with_user()
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, other["session_id"])
            upload = await c.post(
                "/api/documents",
                files={
                    "file": (
                        "p.xlsx",
                        _fixture_bytes("standard.xlsx"),
                        "application/octet-stream",
                    )
                },
            )
            doc_id = upload.json()["document"]["id"]

            c.cookies.set(COOKIE_NAME, setup["session_id"])
            response = await c.post(f"/api/documents/{doc_id}/reparse")
        assert response.status_code == 404
        assert response.json() == {"error": "documento no encontrado"}
    finally:
        await cleanup_node(other["node_id"], other["user_id"])


@pytest.mark.asyncio
async def test_reparse_unauthenticated(pool_lifecycle):
    from uuid import uuid4

    async with client() as c:
        response = await c.post(f"/api/documents/{uuid4()}/reparse")
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}


@pytest.mark.asyncio
async def test_upload_response_does_not_expose_prompt_version(setup):
    """ParseAttemptOut must whitelist payload fields; prompt_version is internal."""
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={
                "file": (
                    "p.xlsx",
                    _fixture_bytes("standard.xlsx"),
                    "application/octet-stream",
                )
            },
        )
    assert "prompt_version" not in response.text


@pytest.mark.asyncio
async def test_low_confidence_xlsx_stays_deterministic(setup):
    """xlsx mime always goes deterministic regardless of confidence — no LLM escalation."""
    # All-rows-skipped xlsx: headers OK, but every row missing product
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Producto", "Cantidad", "Unidad"])
    for _ in range(3):
        ws.append(["", 1, "kg"])
    import io as _io

    buf = _io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("low.xlsx", buf.read(), "application/octet-stream")},
        )
    attempt = response.json()["parse_attempt"]
    assert attempt["strategy"] == "deterministic"
    assert attempt["confidence"] < 1.0




@pytest.mark.asyncio
async def test_delete_document_succeeds(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        upload = await c.post(
            "/api/documents",
            files={
                "file": (
                    "p.xlsx",
                    _fixture_bytes("standard.xlsx"),
                    "application/octet-stream",
                )
            },
        )
        doc_id = upload.json()["document"]["id"]
        response = await c.delete(f"/api/documents/{doc_id}")
    assert response.status_code == 204

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM document WHERE id = %s", (doc_id,)
            )
            (count,) = await cur.fetchone()
    assert count == 0


@pytest.mark.asyncio
async def test_delete_document_other_node_returns_404(setup):
    from uuid import uuid4

    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.delete(f"/api/documents/{uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"error": "documento no encontrado"}


@pytest.mark.asyncio
async def test_delete_document_unauthenticated():
    from uuid import uuid4

    async with client() as c:
        response = await c.delete(f"/api/documents/{uuid4()}")
    assert response.status_code == 401
