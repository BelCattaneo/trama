from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

from trama import db
from trama.config import settings
from trama.main import app
from trama.sessions import create_session


@pytest_asyncio.fixture
async def setup():
    await db.open_pool(settings.database_url, settings.pool_min, settings.pool_max)
    cuit = f"00-{uuid4().hex[:8]}-0"
    email = f"test-{uuid4().hex[:8]}@example.com"
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO node (cuit, display_name, role, latitude, longitude,
                                     address_text, zone_label)
                   VALUES (%s, 'Test Node', 'consumer', -34.6, -58.4,
                           'Some street 123', 'CABA')
                   RETURNING id""",
                (cuit,),
            )
            (node_id,) = await cur.fetchone()
            await cur.execute(
                """INSERT INTO app_user (node_id, email, password_hash, full_name)
                   VALUES (%s, %s, 'never-exposed-hash', 'Test User')
                   RETURNING id""",
                (node_id, email),
            )
            (uid,) = await cur.fetchone()
    session = await create_session(uid)
    yield {
        "user_id": uid,
        "node_id": node_id,
        "session_id": session.id,
        "email": email,
        "cuit": cuit,
    }
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM app_user WHERE id = %s", (uid,))
            await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))
    await db.close_pool()


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_me_authenticated(setup):
    async with _client() as client:
        client.cookies.set("trama_session", setup["session_id"])
        response = await client.get("/api/me")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == setup["email"]
    assert body["user"]["full_name"] == "Test User"
    assert body["node"]["cuit"] == setup["cuit"]
    assert body["node"]["display_name"] == "Test Node"
    assert body["node"]["role"] == "consumer"
    assert body["node"]["zone_label"] == "CABA"
    assert "password_hash" not in response.text
    assert "never-exposed-hash" not in response.text


@pytest.mark.asyncio
async def test_me_unauthenticated_no_cookie():
    async with _client() as client:
        response = await client.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}


@pytest.mark.asyncio
async def test_me_unauthenticated_invalid_cookie(setup):
    async with _client() as client:
        client.cookies.set("trama_session", "completely-invalid-session-id")
        response = await client.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}
