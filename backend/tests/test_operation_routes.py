from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from trama import db
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user


async def _make_parse_attempt(node_id: UUID) -> UUID:
    """Create a document + parse_attempt for the node (required FK for operation)."""
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    node_id,
                    "test.csv",
                    "text/csv",
                    100,
                    "0" * 64,
                    "test-ref",
                ),
            )
            (doc_id,) = await cur.fetchone()
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence,
                                              payload, error_message)
                   VALUES (%s, 'deterministic', 1.0,
                           '{"lines":[],"warnings":[]}'::jsonb, NULL)
                   RETURNING id""",
                (doc_id,),
            )
            (pa_id,) = await cur.fetchone()
    return pa_id


async def _insert_operation(
    node_id: UUID,
    *,
    kind: str = "order",
    operation_date: date | None = None,
    confirmed_at: datetime | None = None,
    lines: list[tuple[str, float, str | None]] | None = None,
) -> UUID:
    pa_id = await _make_parse_attempt(node_id)
    op_date = operation_date or date(2026, 6, 15)
    confirmed = confirmed_at or datetime.now(UTC)
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO operation (node_id, parse_attempt_id, kind,
                                          operation_date, status, confirmed_at)
                   VALUES (%s, %s, %s, %s, 'confirmed', %s)
                   RETURNING id""",
                (node_id, pa_id, kind, op_date, confirmed),
            )
            (op_id,) = await cur.fetchone()
            for idx, (product, quantity, unit) in enumerate(lines or [], start=1):
                await cur.execute(
                    """INSERT INTO operation_line (operation_id, product, quantity,
                                                   unit, line_no)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (op_id, product, quantity, unit, idx),
                )
    return op_id


@pytest_asyncio.fixture
async def setup(node_user):
    yield node_user


# ---------- GET /api/operations ----------


@pytest.mark.asyncio
async def test_list_unauthenticated_returns_401(pool_lifecycle):
    async with client() as c:
        response = await c.get("/api/operations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_empty_returns_empty_items_and_zero_total(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/operations")
    assert response.status_code == 200
    body = response.json()
    assert body == {"items": [], "total": 0}


@pytest.mark.asyncio
async def test_list_returns_items_sorted_by_confirmed_at_desc(setup):
    older = datetime(2026, 6, 1, tzinfo=UTC)
    newer = datetime(2026, 6, 15, tzinfo=UTC)
    await _insert_operation(
        setup["node_id"], confirmed_at=older, lines=[("zanahoria", 1.0, "kg")]
    )
    await _insert_operation(
        setup["node_id"],
        confirmed_at=newer,
        lines=[("tomate", 2.0, "kg"), ("lechuga", 3.0, "unidad")],
    )

    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/operations")
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["line_count"] == 2
    assert body["items"][1]["line_count"] == 1


@pytest.mark.asyncio
async def test_list_only_shows_own_operations(setup):
    other = await make_node_with_user()
    try:
        await _insert_operation(other["node_id"], lines=[("ajeno", 1.0, "kg")])
        await _insert_operation(setup["node_id"], lines=[("mio", 2.0, "kg")])

        async with client() as c:
            c.cookies.set(COOKIE_NAME, setup["session_id"])
            response = await c.get("/api/operations")
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
    finally:
        await cleanup_node(other["node_id"], other["user_id"])


@pytest.mark.asyncio
async def test_list_limit_and_offset(setup):
    for i in range(5):
        await _insert_operation(
            setup["node_id"],
            confirmed_at=datetime(2026, 6, i + 1, tzinfo=UTC),
            lines=[("p", 1.0, "kg")],
        )

    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        first = await c.get("/api/operations?limit=2&offset=0")
        second = await c.get("/api/operations?limit=2&offset=2")
    assert first.json()["total"] == 5
    assert len(first.json()["items"]) == 2
    assert second.json()["total"] == 5
    assert len(second.json()["items"]) == 2
    assert first.json()["items"][0]["id"] != second.json()["items"][0]["id"]


@pytest.mark.asyncio
async def test_list_rejects_limit_over_200(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/operations?limit=201")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_rejects_negative_offset(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/operations?offset=-1")
    assert response.status_code == 422


# ---------- GET /api/operations/{id} ----------


@pytest.mark.asyncio
async def test_detail_unauthenticated_returns_401(pool_lifecycle):
    async with client() as c:
        response = await c.get(f"/api/operations/{uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_detail_owner_returns_lines_ordered_by_line_no(setup):
    op_id = await _insert_operation(
        setup["node_id"],
        kind="offer",
        lines=[
            ("tomate", 5.0, "kg"),
            ("lechuga", 3.0, "unidad"),
            ("cebolla", 2.0, "atado"),
        ],
    )

    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/operations/{op_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "offer"
    assert [line["line_no"] for line in body["lines"]] == [1, 2, 3]
    assert [line["product"] for line in body["lines"]] == [
        "tomate",
        "lechuga",
        "cebolla",
    ]
    assert "raw_text" not in body["lines"][0]
    assert "page" not in body["lines"][0]


@pytest.mark.asyncio
async def test_detail_other_node_returns_404_no_leak(setup):
    other = await make_node_with_user()
    try:
        op_id = await _insert_operation(other["node_id"], lines=[("x", 1.0, "kg")])

        async with client() as c:
            c.cookies.set(COOKIE_NAME, setup["session_id"])
            response = await c.get(f"/api/operations/{op_id}")
        assert response.status_code == 404
        assert response.json() == {"error": "operación no encontrada"}
    finally:
        await cleanup_node(other["node_id"], other["user_id"])


@pytest.mark.asyncio
async def test_detail_nonexistent_returns_404(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/operations/{uuid4()}")
    assert response.status_code == 404
