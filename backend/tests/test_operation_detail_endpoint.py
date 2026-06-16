import json
from uuid import uuid4

import pytest
import pytest_asyncio

from trama import db
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user


async def _make_operation(
    node_id,
    *,
    lines: list[dict],
    kind: str = "order",
    operation_date: str = "2026-02-10",
):
    payload = {"lines": [], "warnings": []}
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref)
                   VALUES (%s, 'fix.xlsx',
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           100, %s, 'ab/dummy')
                   RETURNING id""",
                (node_id, uuid4().hex + uuid4().hex[:32]),
            )
            (doc_id,) = await cur.fetchone()
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence, payload)
                   VALUES (%s, 'deterministic', 1.0, %s::jsonb)
                   RETURNING id""",
                (doc_id, json.dumps(payload)),
            )
            (attempt_id,) = await cur.fetchone()
            await cur.execute(
                """INSERT INTO operation (node_id, parse_attempt_id, kind,
                                          operation_date, status, confirmed_at)
                   VALUES (%s, %s, %s, %s, 'confirmed', now())
                   RETURNING id""",
                (node_id, attempt_id, kind, operation_date),
            )
            (operation_id,) = await cur.fetchone()
            for line in lines:
                await cur.execute(
                    """INSERT INTO operation_line
                           (operation_id, product, quantity, unit,
                            raw_text, line_no, page)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        operation_id,
                        line["product"],
                        line["quantity"],
                        line.get("unit"),
                        line.get("raw_text"),
                        line["line_no"],
                        line.get("page"),
                    ),
                )
    return {"doc_id": doc_id, "attempt_id": attempt_id, "operation_id": operation_id}


@pytest_asyncio.fixture
async def setup(node_user):
    lines = [
        {"line_no": 1, "product": "zanahoria", "quantity": 3.5, "unit": "kg", "page": 1},
        {"line_no": 2, "product": "papa", "quantity": 10.0, "unit": "kg", "page": 1},
        {"line_no": 3, "product": "cebolla", "quantity": 5.0, "unit": "kg", "page": 2},
    ]
    extras = await _make_operation(node_user["node_id"], lines=lines)
    yield {**node_user, **extras}


@pytest.mark.asyncio
async def test_owner_three_lines_returns_200_and_ordered(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/operations/{setup['operation_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(setup["operation_id"])
    assert body["kind"] == "order"
    assert body["operation_date"] == "2026-02-10"
    assert body["document_id"] == str(setup["doc_id"])
    assert "confirmed_at" in body
    assert [line["line_no"] for line in body["lines"]] == [1, 2, 3]
    assert [line["product"] for line in body["lines"]] == [
        "zanahoria",
        "papa",
        "cebolla",
    ]


@pytest.mark.asyncio
async def test_owner_lines_with_page_returns_page(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/operations/{setup['operation_id']}")
    assert response.status_code == 200
    pages = [line["page"] for line in response.json()["lines"]]
    assert pages == [1, 1, 2]


@pytest.mark.asyncio
async def test_owner_lines_with_null_page_returns_null(node_user):
    lines = [
        {"line_no": 1, "product": "tomate", "quantity": 2.0, "unit": "kg", "page": None},
        {"line_no": 2, "product": "lechuga", "quantity": 4.0, "unit": "kg"},
    ]
    extras = await _make_operation(node_user["node_id"], lines=lines)
    async with client() as c:
        c.cookies.set(COOKIE_NAME, node_user["session_id"])
        response = await c.get(f"/api/operations/{extras['operation_id']}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["lines"]) == 2
    assert body["lines"][0]["page"] is None
    assert body["lines"][1]["page"] is None


@pytest.mark.asyncio
async def test_non_owner_returns_404(setup):
    other = await make_node_with_user()
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, other["session_id"])
            response = await c.get(f"/api/operations/{setup['operation_id']}")
        assert response.status_code == 404
        assert response.json() == {"error": "operación no encontrada"}
    finally:
        await cleanup_node(other["node_id"], other["user_id"])


@pytest.mark.asyncio
async def test_non_existent_returns_404(node_user):
    missing_id = uuid4()
    async with client() as c:
        c.cookies.set(COOKIE_NAME, node_user["session_id"])
        response = await c.get(f"/api/operations/{missing_id}")
    assert response.status_code == 404
    assert response.json() == {"error": "operación no encontrada"}


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(setup):
    async with client() as c:
        response = await c.get(f"/api/operations/{setup['operation_id']}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_response_includes_document_id_matching_source(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/operations/{setup['operation_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == str(setup["doc_id"])

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT pa.document_id
                   FROM operation o
                   JOIN parse_attempt pa ON pa.id = o.parse_attempt_id
                   WHERE o.id = %s""",
                (setup["operation_id"],),
            )
            (db_doc_id,) = await cur.fetchone()
    assert body["document_id"] == str(db_doc_id)


@pytest.mark.asyncio
async def test_response_does_not_include_raw_text(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/operations/{setup['operation_id']}")
    assert response.status_code == 200
    for line in response.json()["lines"]:
        assert "raw_text" not in line


@pytest.mark.asyncio
async def test_owner_deletes_operation_cascades_lines_and_clears_winner(setup):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE parse_attempt SET is_winner = true WHERE id = %s",
                (setup["attempt_id"],),
            )
        await conn.commit()
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.delete(f"/api/operations/{setup['operation_id']}")
    assert response.status_code == 204
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM operation WHERE id = %s",
                (setup["operation_id"],),
            )
            (op_count,) = await cur.fetchone()
            await cur.execute(
                "SELECT COUNT(*) FROM operation_line WHERE operation_id = %s",
                (setup["operation_id"],),
            )
            (line_count,) = await cur.fetchone()
            await cur.execute(
                "SELECT is_winner FROM parse_attempt WHERE id = %s",
                (setup["attempt_id"],),
            )
            (is_winner,) = await cur.fetchone()
    assert op_count == 0
    assert line_count == 0
    assert is_winner is False


@pytest.mark.asyncio
async def test_delete_operation_unknown_returns_404(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.delete(f"/api/operations/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_operation_owned_by_other_returns_404(setup):
    other = await make_node_with_user()
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, other["session_id"])
            response = await c.delete(f"/api/operations/{setup['operation_id']}")
        assert response.status_code == 404
        async with db.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM operation WHERE id = %s",
                    (setup["operation_id"],),
                )
                (op_count,) = await cur.fetchone()
        assert op_count == 1
    finally:
        await cleanup_node(other["node_id"], other["user_id"])


@pytest.mark.asyncio
async def test_delete_operation_unauthenticated_returns_401(setup):
    async with client() as c:
        response = await c.delete(f"/api/operations/{setup['operation_id']}")
    assert response.status_code == 401
