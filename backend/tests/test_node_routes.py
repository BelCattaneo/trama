from uuid import uuid4

import pytest
import pytest_asyncio

from trama import db
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user


async def _make_extra_node(*, role: str, display_name: str, zone_label: str | None = None) -> dict:
    cuit = f"00-{uuid4().hex[:8]}-x"
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO node (cuit, display_name, role, latitude, longitude,
                                     address_text, zone_label)
                   VALUES (%s, %s, %s, -34.6, -58.4, 'Some address', %s)
                   RETURNING id""",
                (cuit, display_name, role, zone_label),
            )
            (node_id,) = await cur.fetchone()
    return {"id": node_id, "cuit": cuit, "display_name": display_name}


async def _delete_node(node_id) -> None:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))


@pytest_asyncio.fixture
async def session_user(pool_lifecycle):
    data = await make_node_with_user()
    yield data
    await cleanup_node(data["node_id"], data["user_id"])


@pytest.mark.asyncio
async def test_list_producers_unauthenticated_no_cookie(pool_lifecycle):
    async with client() as c:
        response = await c.get("/api/producers")
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}


@pytest.mark.asyncio
async def test_list_producers_returns_only_producer_and_both_roles(session_user):
    extras = []
    try:
        extras.append(await _make_extra_node(role="producer", display_name="Anaranjados"))
        extras.append(await _make_extra_node(role="both", display_name="Bionogal"))
        # session_user is role='consumer' — must not appear in the list
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.get("/api/producers")
        assert response.status_code == 200
        body = response.json()
        names = [p["display_name"] for p in body["producers"]]
        assert "Anaranjados" in names
        assert "Bionogal" in names
        roles = {p["role"] for p in body["producers"]}
        assert roles.issubset({"producer", "both"})
        session_node_id = str(session_user["node_id"])
        assert all(p["id"] != session_node_id for p in body["producers"])
    finally:
        for e in extras:
            await _delete_node(e["id"])


@pytest.mark.asyncio
async def test_list_producers_sorted_alphabetically(session_user):
    extras = []
    try:
        extras.append(await _make_extra_node(role="producer", display_name="Zeta Cooperativa"))
        extras.append(await _make_extra_node(role="producer", display_name="Alfa Cooperativa"))
        extras.append(await _make_extra_node(role="producer", display_name="Mu Cooperativa"))
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.get("/api/producers")
        assert response.status_code == 200
        names = [p["display_name"] for p in response.json()["producers"]]
        relevant = [n for n in names if "Cooperativa" in n]
        assert relevant == sorted(relevant)
    finally:
        for e in extras:
            await _delete_node(e["id"])


@pytest.mark.asyncio
async def test_list_producers_search_by_name_case_insensitive(session_user):
    extras = []
    try:
        extras.append(await _make_extra_node(role="producer", display_name="Nogalito Sur"))
        extras.append(await _make_extra_node(role="producer", display_name="Frutos del Nogal"))
        extras.append(await _make_extra_node(role="producer", display_name="Tomatera"))
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.get("/api/producers", params={"q": "nogal"})
        assert response.status_code == 200
        names = [p["display_name"] for p in response.json()["producers"]]
        assert "Nogalito Sur" in names
        assert "Frutos del Nogal" in names
        assert "Tomatera" not in names
    finally:
        for e in extras:
            await _delete_node(e["id"])


@pytest.mark.asyncio
async def test_list_producers_search_by_cuit(session_user):
    extras = []
    try:
        extras.append(await _make_extra_node(role="producer", display_name="Searchable by CUIT"))
        target_cuit = extras[0]["cuit"]
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.get("/api/producers", params={"q": target_cuit[3:11]})
        assert response.status_code == 200
        body = response.json()
        cuits = [p["cuit"] for p in body["producers"]]
        assert target_cuit in cuits
    finally:
        for e in extras:
            await _delete_node(e["id"])


@pytest.mark.asyncio
async def test_list_producers_search_no_matches_returns_empty(session_user):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, session_user["session_id"])
        response = await c.get(
            "/api/producers", params={"q": "zzz-impossible-substring-xyz"}
        )
    assert response.status_code == 200
    assert response.json() == {"producers": []}
