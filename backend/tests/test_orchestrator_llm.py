import io
import json

import pytest
import pytest_asyncio
from PIL import Image

from trama import db
from trama.sessions import COOKIE_NAME

from .conftest import client


@pytest_asyncio.fixture
async def setup(node_user):
    yield node_user


def _make_jpeg(size=(200, 150), color="white") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _make_multipage_pdf(pages: int) -> bytes:
    imgs = [Image.new("RGB", (200, 300), "white") for _ in range(pages)]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


def _stub_with_response(monkeypatch, payload_dict: dict) -> list[bytes]:
    """Replace LLM stub with one returning fixed JSON. Returns images it was called with."""
    seen_images: list[bytes] = []

    class _FixedClient:
        async def parse_image(self, image_bytes: bytes, prompt: str) -> dict:
            seen_images.append(image_bytes)
            return {
                "text": json.dumps(payload_dict),
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
                "response_id": "resp-test",
            }

    monkeypatch.setattr(
        "trama.parsing.orchestrator.get_llm_client", lambda: _FixedClient()
    )
    return seen_images


def _stub_raising(monkeypatch, exc: Exception) -> None:
    class _RaisingClient:
        async def parse_image(self, image_bytes: bytes, prompt: str) -> dict:
            raise exc

    monkeypatch.setattr(
        "trama.parsing.orchestrator.get_llm_client", lambda: _RaisingClient()
    )


def _stub_text(monkeypatch, text: str) -> None:
    class _TextClient:
        async def parse_image(self, image_bytes: bytes, prompt: str) -> dict:
            return {
                "text": text,
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
                "response_id": None,
            }

    monkeypatch.setattr(
        "trama.parsing.orchestrator.get_llm_client", lambda: _TextClient()
    )


@pytest.mark.asyncio
async def test_jpeg_upload_creates_llm_parse_attempt(setup, monkeypatch):
    payload = {
        "lines": [
            {"product": "tomate", "quantity": 5.0, "unit": "kg", "raw_text": "tomate 5kg"}
        ],
        "warnings": [],
    }
    _stub_with_response(monkeypatch, payload)

    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("foto.jpg", _make_jpeg(), "application/octet-stream")},
        )

    assert response.status_code == 201
    body = response.json()
    attempt = body["parse_attempt"]
    assert attempt is not None
    assert attempt["strategy"] == "llm"
    assert attempt["confidence"] == 1.0
    assert attempt["payload"]["lines"][0]["product"] == "tomate"
    assert attempt["payload"]["lines"][0]["page"] == 1


@pytest.mark.asyncio
async def test_multipage_pdf_tags_lines_per_page(setup, monkeypatch):
    payload = {
        "lines": [
            {"product": "tomate", "quantity": 1.0, "unit": "kg", "raw_text": "t"}
        ],
        "warnings": ["fila incierta"],
    }
    _stub_with_response(monkeypatch, payload)

    pdf = _make_multipage_pdf(3)
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("doc.pdf", pdf, "application/octet-stream")},
        )

    attempt = response.json()["parse_attempt"]
    assert attempt["strategy"] == "llm"
    pages = [line["page"] for line in attempt["payload"]["lines"]]
    assert pages == [1, 2, 3]
    warnings = attempt["payload"]["warnings"]
    assert any(w.startswith("[p1]") for w in warnings)
    assert any(w.startswith("[p3]") for w in warnings)


@pytest.mark.asyncio
async def test_llm_wrapper_failure_persists_failed_attempt(setup, monkeypatch):
    import httpx

    _stub_raising(monkeypatch, httpx.ConnectError("network down"))

    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("foto.jpg", _make_jpeg(), "application/octet-stream")},
        )

    assert response.status_code == 201
    attempt = response.json()["parse_attempt"]
    assert attempt["confidence"] == 0.0
    assert attempt["payload"] is None
    assert "ConnectError" in attempt["error_message"]


@pytest.mark.asyncio
async def test_invalid_json_response_persists_failed_attempt(setup, monkeypatch):
    _stub_text(monkeypatch, "not json at all {")

    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("foto.jpg", _make_jpeg(), "application/octet-stream")},
        )

    attempt = response.json()["parse_attempt"]
    assert attempt["confidence"] == 0.0
    assert attempt["payload"] is None
    assert "LLMResponseError" in attempt["error_message"]


@pytest.mark.asyncio
async def test_heic_upload_persists_and_routes_through_llm(setup, monkeypatch):
    """Catches the E5 regression where document.mime_type CHECK rejected image/heic."""
    payload = {"lines": [], "warnings": []}
    _stub_with_response(monkeypatch, payload)

    heic = b"\x00\x00\x00\x20ftypheic" + b"\x00" * 24
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("foto.heic", heic, "application/octet-stream")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["document"]["mime_type"] == "image/heic"
    assert body["parse_attempt"]["strategy"] == "llm"


@pytest.mark.asyncio
async def test_corrupt_pdf_persists_preprocess_failed_attempt(setup, monkeypatch):
    payload = {"lines": [], "warnings": []}
    _stub_with_response(monkeypatch, payload)

    corrupt = b"%PDF-1.4\nnot really a pdf\n"
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("bad.pdf", corrupt, "application/octet-stream")},
        )

    assert response.status_code == 201
    attempt = response.json()["parse_attempt"]
    assert attempt["strategy"] == "llm"
    assert attempt["confidence"] == 0.0
    assert attempt["payload"] is None
    assert attempt["error_message"].startswith("preprocess failed: ")


@pytest.mark.asyncio
async def test_pdf_mixed_page_success_and_failure(setup, monkeypatch):
    clean_payload = {
        "lines": [
            {"product": "tomate", "quantity": 1.0, "unit": "kg", "raw_text": "t"}
        ],
        "warnings": [],
    }

    calls = {"count": 0}

    class _MixedClient:
        async def parse_image(self, image_bytes: bytes, prompt: str) -> dict:
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("simulated page 2 crash")
            return {
                "text": json.dumps(clean_payload),
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
                "response_id": None,
            }

    monkeypatch.setattr(
        "trama.parsing.orchestrator.get_llm_client", lambda: _MixedClient()
    )

    pdf = _make_multipage_pdf(3)
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("mixed.pdf", pdf, "application/octet-stream")},
        )

    attempt = response.json()["parse_attempt"]
    assert attempt["strategy"] == "llm"
    pages_with_lines = [line["page"] for line in attempt["payload"]["lines"]]
    assert pages_with_lines == [1, 3]
    warnings = attempt["payload"]["warnings"]
    assert any("[p2] página falló" in w for w in warnings)
    assert attempt["error_message"] is None


@pytest.mark.asyncio
async def test_reparse_llm_document_creates_new_attempt(setup, monkeypatch):
    payload = {
        "lines": [
            {"product": "cebolla", "quantity": 2.0, "unit": "atado", "raw_text": "c"}
        ],
        "warnings": [],
    }
    _stub_with_response(monkeypatch, payload)

    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        upload = await c.post(
            "/api/documents",
            files={"file": ("foto.jpg", _make_jpeg(), "application/octet-stream")},
        )
        doc_id = upload.json()["document"]["id"]
        reparse = await c.post(f"/api/documents/{doc_id}/reparse")

    assert reparse.status_code == 200
    assert reparse.json()["parse_attempt"]["strategy"] == "llm"

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM parse_attempt WHERE document_id = %s",
                (doc_id,),
            )
            (count,) = await cur.fetchone()
    assert count == 2
