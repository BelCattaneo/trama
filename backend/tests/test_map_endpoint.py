from uuid import uuid4

import pytest
import pytest_asyncio

from trama import db
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user


async def _insert_node(role="producer", display_name=None, zone_label=None):
    cuit = f"00-{uuid4().hex[:8]}-x"
    name = display_name or f"Node-{uuid4().hex[:6]}"
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO node (cuit, display_name, role, latitude, longitude,
                                     address_text, zone_label)
                   VALUES (%s, %s, %s, -34.6, -58.4, 'X', %s)
                   RETURNING id""",
                (cuit, name, role, zone_label),
            )
            (node_id,) = await cur.fetchone()
    return node_id


async def _delete_node(node_id):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM operation WHERE node_id = %s OR supplier_node_id = %s",
                (node_id, node_id),
            )
            await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))


async def _insert_operation_with_lines(
    *, buyer_id, supplier_id, products, days_ago=0
):
    """Insert an operation under buyer_id (node_id), supplied by supplier_id, with line items."""
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref)
                   VALUES (%s, 'f.xlsx',
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           1, %s, 'ab/x')
                   RETURNING id""",
                (buyer_id, uuid4().hex + uuid4().hex[:32]),
            )
            (doc_id,) = await cur.fetchone()
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence,
                                              payload, is_winner)
                   VALUES (%s, 'deterministic', 1.0, NULL, true)
                   RETURNING id""",
                (doc_id,),
            )
            (attempt_id,) = await cur.fetchone()
            await cur.execute(
                """INSERT INTO operation (node_id, parse_attempt_id, kind, operation_date,
                                          status, supplier_node_id, confirmed_at)
                   VALUES (%s, %s, 'order', current_date, 'confirmed', %s,
                           now() - (%s || ' days')::interval)
                   RETURNING id""",
                (buyer_id, attempt_id, supplier_id, days_ago),
            )
            (operation_id,) = await cur.fetchone()
            for idx, product in enumerate(products, start=1):
                await cur.execute(
                    """INSERT INTO operation_line
                           (operation_id, product, quantity, unit, line_no)
                       VALUES (%s, %s, 1.0, 'kg', %s)""",
                    (operation_id, product, idx),
                )
    return operation_id


@pytest_asyncio.fixture
async def session_user(pool_lifecycle):
    data = await make_node_with_user()
    yield data
    await cleanup_node(data["node_id"], data["user_id"])


@pytest.mark.asyncio
async def test_map_unauthenticated(pool_lifecycle):
    async with client() as c:
        response = await c.get("/api/map")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_map_returns_all_nodes_with_zero_counts(session_user):
    """Nodes without operations show counts=0 and empty top_products."""
    extras = [await _insert_node(role="producer", display_name="Productor sin pedidos")]
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.get("/api/map")
        assert response.status_code == 200
        body = response.json()
        names = {n["display_name"]: n for n in body["nodes"]}
        assert "Productor sin pedidos" in names
        n = names["Productor sin pedidos"]
        assert n["orders_last_week"] == 0
        assert n["orders_total"] == 0
        assert n["top_products"] == []
        assert n["latitude"] == -34.6
        assert n["longitude"] == -58.4
    finally:
        for e in extras:
            await _delete_node(e)


@pytest.mark.asyncio
async def test_map_counts_orders_last_week_vs_total(session_user):
    supplier = await _insert_node(role="producer", display_name="Supplier Counts")
    try:
        await _insert_operation_with_lines(
            buyer_id=session_user["node_id"], supplier_id=supplier,
            products=["tomate"], days_ago=1,
        )
        await _insert_operation_with_lines(
            buyer_id=session_user["node_id"], supplier_id=supplier,
            products=["tomate"], days_ago=3,
        )
        await _insert_operation_with_lines(
            buyer_id=session_user["node_id"], supplier_id=supplier,
            products=["zanahoria"], days_ago=20,
        )
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.get("/api/map")
        node = next(n for n in response.json()["nodes"]
                    if n["display_name"] == "Supplier Counts")
        assert node["orders_last_week"] == 2
        assert node["orders_total"] == 3
    finally:
        await _delete_node(supplier)


@pytest.mark.asyncio
async def test_map_top_products_by_distinct_operation_count(session_user):
    """Top products ranks by COUNT(DISTINCT operation), not line frequency."""
    supplier = await _insert_node(role="producer", display_name="Top Products")
    try:
        # 3 ops with tomate, 1 op with zanahoria (but 5 lines of zanahoria)
        for _ in range(3):
            await _insert_operation_with_lines(
                buyer_id=session_user["node_id"], supplier_id=supplier,
                products=["tomate"],
            )
        await _insert_operation_with_lines(
            buyer_id=session_user["node_id"], supplier_id=supplier,
            products=["zanahoria"] * 5,
        )
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.get("/api/map")
        node = next(n for n in response.json()["nodes"]
                    if n["display_name"] == "Top Products")
        assert node["top_products"][0] == "tomate"
        assert "zanahoria" in node["top_products"]
    finally:
        await _delete_node(supplier)


@pytest.mark.asyncio
async def test_map_top_products_capped_at_three(session_user):
    supplier = await _insert_node(role="producer", display_name="Many Products")
    try:
        for product in ["a", "b", "c", "d", "e"]:
            await _insert_operation_with_lines(
                buyer_id=session_user["node_id"], supplier_id=supplier,
                products=[product],
            )
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.get("/api/map")
        node = next(n for n in response.json()["nodes"]
                    if n["display_name"] == "Many Products")
        assert len(node["top_products"]) == 3
    finally:
        await _delete_node(supplier)


@pytest.mark.asyncio
async def test_map_consumer_only_node_has_zero_supply_stats(session_user):
    consumer = await _insert_node(role="consumer", display_name="Solo Consume")
    try:
        # session_user is consumer; create an operation where it BUYS from no supplier
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.get("/api/map")
        node = next(n for n in response.json()["nodes"]
                    if n["display_name"] == "Solo Consume")
        assert node["orders_last_week"] == 0
        assert node["orders_total"] == 0
        assert node["top_products"] == []
        assert node["role"] == "consumer"
    finally:
        await _delete_node(consumer)


@pytest.mark.asyncio
async def test_map_sorted_alphabetically(session_user):
    extras = [
        await _insert_node(role="producer", display_name="ZZZ Last"),
        await _insert_node(role="producer", display_name="AAA First"),
    ]
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.get("/api/map")
        names = [n["display_name"] for n in response.json()["nodes"]]
        assert names.index("AAA First") < names.index("ZZZ Last")
    finally:
        for e in extras:
            await _delete_node(e)
