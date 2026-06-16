from uuid import uuid4

import pytest
import pytest_asyncio

from trama import db
from trama.geocode import GeocodingResult
from trama.rate_limit import _upload_limiter
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user

VALID_CUIT_A = "20-00000002-8"
VALID_CUIT_B = "20-00000003-6"
INVALID_CUIT = "20-00000000-0"


def _ok_geocode(addr):
    return GeocodingResult(latitude=-34.6, longitude=-58.4, zone_label="CABA")


def _patch_geocode(monkeypatch, fn):
    async def _impl(addr):
        return fn(addr)
    monkeypatch.setattr("trama.node_routes.geocode", _impl)


@pytest_asyncio.fixture
async def session_user(pool_lifecycle):
    _upload_limiter.reset()
    data = await make_node_with_user()
    yield data
    await cleanup_node(data["node_id"], data["user_id"])


async def _delete_node(node_id) -> None:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))


@pytest.mark.asyncio
async def test_create_node_unauthenticated(pool_lifecycle):
    async with client() as c:
        response = await c.post(
            "/api/nodes",
            json={
                "cuit": VALID_CUIT_A,
                "display_name": "Nogalito",
                "address": "Av. de Mayo 760",
                "role": "producer",
            },
        )
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}


@pytest.mark.asyncio
async def test_create_producer_happy_path(session_user, monkeypatch):
    _patch_geocode(monkeypatch, _ok_geocode)
    created_id = None
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.post(
                "/api/nodes",
                json={
                    "cuit": VALID_CUIT_A,
                    "display_name": "Cooperativa Nogalito",
                    "address": "Av. de Mayo 760, CABA",
                    "role": "producer",
                },
            )
        assert response.status_code == 201
        body = response.json()
        assert body["display_name"] == "Cooperativa Nogalito"
        assert body["cuit"] == VALID_CUIT_A
        assert body["role"] == "producer"
        assert body["zone_label"] == "CABA"
        created_id = body["id"]
    finally:
        if created_id:
            await _delete_node(created_id)


@pytest.mark.asyncio
async def test_create_role_both_accepted(session_user, monkeypatch):
    _patch_geocode(monkeypatch, _ok_geocode)
    created_id = None
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.post(
                "/api/nodes",
                json={
                    "cuit": VALID_CUIT_B,
                    "display_name": "Mixta",
                    "address": "Calle 1",
                    "role": "both",
                },
            )
        assert response.status_code == 201
        assert response.json()["role"] == "both"
        created_id = response.json()["id"]
    finally:
        if created_id:
            await _delete_node(created_id)


@pytest.mark.asyncio
async def test_create_node_invalid_cuit(session_user, monkeypatch):
    _patch_geocode(monkeypatch, _ok_geocode)
    async with client() as c:
        c.cookies.set(COOKIE_NAME, session_user["session_id"])
        response = await c.post(
            "/api/nodes",
            json={
                "cuit": INVALID_CUIT,
                "display_name": "X",
                "address": "Calle 1",
                "role": "producer",
            },
        )
    assert response.status_code == 400
    assert response.json() == {"error": "CUIT inválido"}


@pytest.mark.asyncio
async def test_create_node_duplicate_cuit(session_user, monkeypatch):
    _patch_geocode(monkeypatch, _ok_geocode)
    created_id = None
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            first = await c.post(
                "/api/nodes",
                json={
                    "cuit": VALID_CUIT_A,
                    "display_name": "First",
                    "address": "Calle 1",
                    "role": "producer",
                },
            )
            assert first.status_code == 201
            created_id = first.json()["id"]
            second = await c.post(
                "/api/nodes",
                json={
                    "cuit": VALID_CUIT_A,
                    "display_name": "Duplicate",
                    "address": "Calle 1",
                    "role": "producer",
                },
            )
        assert second.status_code == 409
        assert second.json() == {"error": "CUIT ya registrado"}
    finally:
        if created_id:
            await _delete_node(created_id)


@pytest.mark.asyncio
async def test_create_node_geocoding_failure(session_user, monkeypatch):
    _patch_geocode(monkeypatch, lambda _: None)
    async with client() as c:
        c.cookies.set(COOKIE_NAME, session_user["session_id"])
        response = await c.post(
            "/api/nodes",
            json={
                "cuit": VALID_CUIT_A,
                "display_name": "Sin ubicación",
                "address": "Pluto",
                "role": "producer",
            },
        )
    assert response.status_code == 400
    assert response.json() == {"error": "no pudimos ubicar la dirección"}


@pytest.mark.asyncio
async def test_create_node_role_consumer_rejected_at_validation(session_user, monkeypatch):
    _patch_geocode(monkeypatch, _ok_geocode)
    async with client() as c:
        c.cookies.set(COOKIE_NAME, session_user["session_id"])
        response = await c.post(
            "/api/nodes",
            json={
                "cuit": VALID_CUIT_A,
                "display_name": "Consumer attempt",
                "address": "Calle 1",
                "role": "consumer",
            },
        )
    assert response.status_code == 422
    body = response.json()
    assert any("role" in str(d) for d in body.get("detail", []))


@pytest.mark.asyncio
async def test_create_node_does_not_create_app_user(session_user, monkeypatch):
    _patch_geocode(monkeypatch, _ok_geocode)
    created_id = None
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, session_user["session_id"])
            response = await c.post(
                "/api/nodes",
                json={
                    "cuit": VALID_CUIT_A,
                    "display_name": f"NoUser-{uuid4().hex[:6]}",
                    "address": "Calle 1",
                    "role": "producer",
                },
            )
        assert response.status_code == 201
        created_id = response.json()["id"]
        async with db.cursor() as cur:
            await cur.execute(
                "SELECT count(*) FROM app_user WHERE node_id = %s", (created_id,)
            )
            (n,) = await cur.fetchone()
        assert n == 0
    finally:
        if created_id:
            await _delete_node(created_id)
