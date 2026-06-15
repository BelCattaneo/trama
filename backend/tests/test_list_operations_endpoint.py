from uuid import uuid4

import pytest
import pytest_asyncio

from trama import db
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user


async def _insert_operation(
    node_id,
    *,
    kind: str = "order",
    operation_date: str = "2026-01-01",
    confirmed_offset_seconds: int = 0,
    line_count: int = 0,
):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref)
                   VALUES (%s, 'op.xlsx',
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           100, %s, 'ab/dummy')
                   RETURNING id""",
                (node_id, uuid4().hex + uuid4().hex[:32]),
            )
            (doc_id,) = await cur.fetchone()
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence)
                   VALUES (%s, 'deterministic', 1.0)
                   RETURNING id""",
                (doc_id,),
            )
            (attempt_id,) = await cur.fetchone()
            await cur.execute(
                """INSERT INTO operation (node_id, parse_attempt_id, kind,
                                          operation_date, status, confirmed_at)
                   VALUES (%s, %s, %s, %s, 'confirmed',
                           now() + (%s || ' seconds')::interval)
                   RETURNING id""",
                (node_id, attempt_id, kind, operation_date, confirmed_offset_seconds),
            )
            (op_id,) = await cur.fetchone()
            for i in range(line_count):
                await cur.execute(
                    """INSERT INTO operation_line
                           (operation_id, product, quantity, unit, line_no)
                       VALUES (%s, %s, 1.0, 'kg', %s)""",
                    (op_id, f"product-{i}", i + 1),
                )
    return op_id


@pytest_asyncio.fixture
async def setup(node_user):
    yield node_user


@pytest.mark.asyncio
async def test_list_empty(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/operations")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


@pytest.mark.asyncio
async def test_list_three_operations_sorted_with_line_counts(setup):
    await _insert_operation(
        setup["node_id"], confirmed_offset_seconds=-100, line_count=2
    )
    mid_id = await _insert_operation(
        setup["node_id"], confirmed_offset_seconds=-50, line_count=5
    )
    new_id = await _insert_operation(
        setup["node_id"], confirmed_offset_seconds=0, line_count=0
    )
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/operations")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert body["items"][0]["id"] == str(new_id)
    assert body["items"][0]["line_count"] == 0
    assert body["items"][1]["id"] == str(mid_id)
    assert body["items"][1]["line_count"] == 5
    assert body["items"][2]["line_count"] == 2
    for item in body["items"]:
        assert set(item.keys()) == {
            "id",
            "kind",
            "operation_date",
            "confirmed_at",
            "line_count",
        }


@pytest.mark.asyncio
async def test_other_nodes_operations_excluded(pool_lifecycle):
    a = await make_node_with_user()
    b = await make_node_with_user()
    try:
        await _insert_operation(b["node_id"], line_count=3)
        await _insert_operation(b["node_id"], line_count=1)
        async with client() as c:
            c.cookies.set(COOKIE_NAME, a["session_id"])
            response = await c.get("/api/operations")
        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0}
    finally:
        await cleanup_node(a["node_id"], a["user_id"])
        await cleanup_node(b["node_id"], b["user_id"])


@pytest.mark.asyncio
async def test_limit_paginates_but_total_is_full(setup):
    for offset in (-300, -200, -100):
        await _insert_operation(
            setup["node_id"], confirmed_offset_seconds=offset, line_count=1
        )
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/operations?limit=2")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3


@pytest.mark.asyncio
async def test_limit_capped_at_200(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/operations?limit=500")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_offset_skips_first(setup):
    older_id = await _insert_operation(
        setup["node_id"], confirmed_offset_seconds=-100, line_count=1
    )
    newer_id = await _insert_operation(
        setup["node_id"], confirmed_offset_seconds=0, line_count=2
    )
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/operations?offset=1")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(older_id)
    assert body["total"] == 2
    assert str(newer_id) not in [item["id"] for item in body["items"]]


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(pool_lifecycle):
    async with client() as c:
        response = await c.get("/api/operations")
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}
