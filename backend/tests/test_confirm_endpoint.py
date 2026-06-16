import json
from uuid import uuid4

import httpx
import psycopg
import pytest
import pytest_asyncio
from httpx import ASGITransport

from trama import db
from trama.main import app
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user

PAYLOAD = {
    "lines": [
        {
            "product": "zanahoria",
            "quantity": 3.5,
            "unit": "kg",
            "raw_text": "zanahoria | 3.5 | kg",
            "page": 1,
        },
        {
            "product": "papa",
            "quantity": 10.0,
            "unit": "kg",
            "raw_text": "papa | 10 | kg",
            "page": 1,
        },
    ],
    "warnings": [],
}


async def _make_document_with_attempt(node_id):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref)
                   VALUES (%s, 'fix.xlsx',
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           100, %s, 'ab/dummy')
                   RETURNING id, uploaded_at""",
                (node_id, uuid4().hex + uuid4().hex[:32]),
            )
            doc_id, uploaded_at = await cur.fetchone()
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence, payload)
                   VALUES (%s, 'deterministic', 1.0, %s::jsonb)
                   RETURNING id""",
                (doc_id, json.dumps(PAYLOAD)),
            )
            (attempt_id,) = await cur.fetchone()
    return doc_id, attempt_id, uploaded_at


@pytest_asyncio.fixture
async def setup(node_user):
    doc_id, attempt_id, uploaded_at = await _make_document_with_attempt(
        node_user["node_id"]
    )
    yield {
        **node_user,
        "doc_id": doc_id,
        "attempt_id": attempt_id,
        "uploaded_at": uploaded_at,
    }


def _good_body(operation_date: str | None = None) -> dict:
    body = {
        "lines": [
            {
                "line_no": 0,
                "product": "zanahoria",
                "quantity": 3.5,
                "unit": "kg",
                "raw_text": "zanahoria | 3.5 | kg",
                "page": 1,
            },
            {
                "line_no": 1,
                "product": "papa",
                "quantity": 10.0,
                "unit": "kg",
                "raw_text": "papa | 10 | kg",
                "page": 1,
            },
        ],
        "corrections": [],
    }
    if operation_date is not None:
        body["operation_date"] = operation_date
    return body


@pytest.mark.asyncio
async def test_confirm_owner_happy_path(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm",
            json=_good_body(operation_date="2026-02-10"),
        )
    assert response.status_code == 201
    body = response.json()
    operation_id = body["operation_id"]
    assert operation_id

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT node_id, parse_attempt_id, kind, status, operation_date
                   FROM operation WHERE id = %s""",
                (operation_id,),
            )
            op_row = await cur.fetchone()
            await cur.execute(
                """SELECT line_no, product, quantity, unit
                   FROM operation_line
                   WHERE operation_id = %s
                   ORDER BY line_no""",
                (operation_id,),
            )
            line_rows = await cur.fetchall()
            await cur.execute(
                "SELECT is_winner FROM parse_attempt WHERE id = %s",
                (setup["attempt_id"],),
            )
            (is_winner,) = await cur.fetchone()
            await cur.execute(
                "SELECT COUNT(*) FROM correction WHERE parse_attempt_id = %s",
                (setup["attempt_id"],),
            )
            (corr_count,) = await cur.fetchone()

    assert op_row[0] == setup["node_id"]
    assert op_row[1] == setup["attempt_id"]
    assert op_row[2] == "order"
    assert op_row[3] == "confirmed"
    assert op_row[4].isoformat() == "2026-02-10"
    assert [r[0] for r in line_rows] == [1, 2]
    assert [r[1] for r in line_rows] == ["zanahoria", "papa"]
    assert is_winner is True
    assert corr_count == 0


@pytest.mark.asyncio
async def test_confirm_non_owner_returns_404(setup):
    other = await make_node_with_user()
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, other["session_id"])
            response = await c.post(
                f"/api/documents/{setup['doc_id']}/confirm", json=_good_body()
            )
        assert response.status_code == 404
        assert response.json() == {"error": "documento no encontrado"}
    finally:
        await cleanup_node(other["node_id"], other["user_id"])


@pytest.mark.asyncio
async def test_confirm_unauthenticated_returns_401(setup):
    async with client() as c:
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=_good_body()
        )
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}


@pytest.mark.asyncio
async def test_confirm_already_confirmed_returns_409(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        first = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=_good_body()
        )
        assert first.status_code == 201
        second = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=_good_body()
        )
    assert second.status_code == 409
    assert second.json() == {"error": "ya confirmado"}


@pytest.mark.asyncio
async def test_confirm_empty_lines_returns_400(setup):
    body = _good_body()
    body["lines"] = []
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=body
        )
    assert response.status_code == 400
    assert response.json() == {"error": "se necesita al menos una línea"}


@pytest.mark.asyncio
async def test_confirm_zero_quantity_returns_400(setup):
    body = _good_body()
    body["lines"][1]["quantity"] = 0
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=body
        )
    assert response.status_code == 400
    assert response.json() == {"error": "línea 2 con cantidad inválida"}


@pytest.mark.asyncio
async def test_confirm_empty_product_returns_400(setup):
    body = _good_body()
    body["lines"][0]["product"] = ""
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=body
        )
    assert response.status_code == 400
    assert response.json() == {"error": "línea 1 con producto sin completar"}


@pytest.mark.asyncio
async def test_confirm_unreadable_product_returns_400(setup):
    body = _good_body()
    body["lines"][0]["product"] = "unreadable"
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=body
        )
    assert response.status_code == 400
    assert response.json() == {"error": "línea 1 con producto sin completar"}


@pytest.mark.asyncio
async def test_confirm_defaults_operation_date_from_uploaded_at(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=_good_body()
        )
    assert response.status_code == 201
    operation_id = response.json()["operation_id"]

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT operation_date FROM operation WHERE id = %s",
                (operation_id,),
            )
            (op_date,) = await cur.fetchone()
            await cur.execute(
                """SELECT (uploaded_at AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
                   FROM document WHERE id = %s""",
                (setup["doc_id"],),
            )
            (expected_date,) = await cur.fetchone()
    assert op_date == expected_date


@pytest.mark.asyncio
async def test_confirm_persists_corrections(setup):
    body = _good_body()
    body["corrections"] = [
        {
            "line_no": 0,
            "field": "product",
            "original_value": "zanaoria",
            "corrected_value": "zanahoria",
        },
        {
            "line_no": 1,
            "field": "quantity",
            "original_value": "9",
            "corrected_value": "10",
        },
    ]
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=body
        )
    assert response.status_code == 201

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT line_no, field, original_value, corrected_value
                   FROM correction
                   WHERE parse_attempt_id = %s
                   ORDER BY line_no, field""",
                (setup["attempt_id"],),
            )
            rows = await cur.fetchall()
    assert len(rows) == 2
    assert (rows[0][0], rows[0][1], rows[0][2], rows[0][3]) == (
        0,
        "product",
        "zanaoria",
        "zanahoria",
    )
    assert (rows[1][0], rows[1][1], rows[1][2], rows[1][3]) == (
        1,
        "quantity",
        "9",
        "10",
    )


@pytest.mark.asyncio
async def test_confirm_rolls_back_on_correction_failure(setup, monkeypatch):
    body = _good_body()
    body["corrections"] = [
        {
            "line_no": 0,
            "field": "product",
            "original_value": "x",
            "corrected_value": "y",
        }
    ]

    real_execute = psycopg.AsyncCursor.execute

    async def flaky_execute(self, query, params=None, *args, **kwargs):
        if "INSERT INTO correction" in query:
            raise psycopg.errors.OperationalError("simulated failure")
        return await real_execute(self, query, params, *args, **kwargs)

    monkeypatch.setattr(psycopg.AsyncCursor, "execute", flaky_execute)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=body
        )
    assert response.status_code == 500

    monkeypatch.undo()

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM operation WHERE node_id = %s",
                (setup["node_id"],),
            )
            (op_count,) = await cur.fetchone()
            await cur.execute(
                "SELECT COUNT(*) FROM correction WHERE parse_attempt_id = %s",
                (setup["attempt_id"],),
            )
            (corr_count,) = await cur.fetchone()
            await cur.execute(
                "SELECT is_winner FROM parse_attempt WHERE id = %s",
                (setup["attempt_id"],),
            )
            (is_winner,) = await cur.fetchone()
    assert op_count == 0
    assert corr_count == 0
    assert is_winner is False


async def _make_producer_node(role="producer", display_name="Productor X"):
    cuit = f"00-{uuid4().hex[:8]}-x"
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO node (cuit, display_name, role, latitude, longitude,
                                     address_text, zone_label)
                   VALUES (%s, %s, %s, -34.6, -58.4, 'X', 'CABA')
                   RETURNING id""",
                (cuit, display_name, role),
            )
            (node_id,) = await cur.fetchone()
    return node_id


async def _delete_node(node_id):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))


@pytest.mark.asyncio
async def test_confirm_with_supplier_node_id_persists_link(setup):
    supplier_id = await _make_producer_node()
    try:
        body = _good_body(operation_date="2026-02-10")
        body["supplier_node_id"] = str(supplier_id)
        async with client() as c:
            c.cookies.set(COOKIE_NAME, setup["session_id"])
            response = await c.post(
                f"/api/documents/{setup['doc_id']}/confirm", json=body
            )
        assert response.status_code == 201
        operation_id = response.json()["operation_id"]
        async with db.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT supplier_node_id FROM operation WHERE id = %s",
                    (operation_id,),
                )
                (linked,) = await cur.fetchone()
        assert linked == supplier_id
    finally:
        await _delete_node(supplier_id)


@pytest.mark.asyncio
async def test_confirm_with_role_both_supplier_accepted(setup):
    supplier_id = await _make_producer_node(role="both")
    try:
        body = _good_body()
        body["supplier_node_id"] = str(supplier_id)
        async with client() as c:
            c.cookies.set(COOKIE_NAME, setup["session_id"])
            response = await c.post(
                f"/api/documents/{setup['doc_id']}/confirm", json=body
            )
        assert response.status_code == 201
    finally:
        await _delete_node(supplier_id)


@pytest.mark.asyncio
async def test_confirm_with_consumer_role_supplier_rejected(setup):
    consumer_id = await _make_producer_node(role="consumer")
    try:
        body = _good_body()
        body["supplier_node_id"] = str(consumer_id)
        async with client() as c:
            c.cookies.set(COOKIE_NAME, setup["session_id"])
            response = await c.post(
                f"/api/documents/{setup['doc_id']}/confirm", json=body
            )
        assert response.status_code == 400
        assert response.json() == {"error": "el nodo seleccionado no es productor"}
        async with db.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM operation WHERE node_id = %s",
                    (setup["node_id"],),
                )
                (op_count,) = await cur.fetchone()
        assert op_count == 0
    finally:
        await _delete_node(consumer_id)


@pytest.mark.asyncio
async def test_confirm_with_nonexistent_supplier_rejected(setup):
    body = _good_body()
    body["supplier_node_id"] = str(uuid4())
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=body
        )
    assert response.status_code == 400
    assert response.json() == {"error": "productor no encontrado"}


@pytest.mark.asyncio
async def test_confirm_without_supplier_node_id_persists_null(setup):
    body = _good_body()
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            f"/api/documents/{setup['doc_id']}/confirm", json=body
        )
    assert response.status_code == 201
    operation_id = response.json()["operation_id"]
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT supplier_node_id FROM operation WHERE id = %s",
                (operation_id,),
            )
            (linked,) = await cur.fetchone()
    assert linked is None
