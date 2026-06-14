from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

from trama import db
from trama.config import settings
from trama.main import app
from trama.passwords import hash_password
from trama.sessions import COOKIE_NAME

PASSWORD = "correct horse battery staple"


@pytest_asyncio.fixture
async def setup():
    await db.open_pool(settings.database_url, settings.pool_min, settings.pool_max)
    cuit = f"00-{uuid4().hex[:8]}-0"
    email = f"test-{uuid4().hex[:8]}@example.com"
    password_hash = hash_password(PASSWORD)
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO node (cuit, display_name, role, latitude, longitude)
                   VALUES (%s, 'Test Node', 'consumer', 0, 0) RETURNING id""",
                (cuit,),
            )
            (node_id,) = await cur.fetchone()
            await cur.execute(
                """INSERT INTO app_user (node_id, email, password_hash)
                   VALUES (%s, %s, %s) RETURNING id""",
                (node_id, email, password_hash),
            )
            (uid,) = await cur.fetchone()
    yield {"user_id": uid, "node_id": node_id, "email": email}
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM app_user WHERE id = %s", (uid,))
            await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))
    await db.close_pool()


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_login_success_sets_cookie(setup):
    async with _client() as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": setup["email"], "password": PASSWORD},
        )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_login_bad_password(setup):
    async with _client() as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": setup["email"], "password": "wrong"},
        )
    assert response.status_code == 401
    assert response.json() == {"error": "credenciales inválidas"}
    assert COOKIE_NAME not in response.cookies


@pytest.mark.asyncio
async def test_login_unknown_email(setup):
    async with _client() as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": PASSWORD},
        )
    assert response.status_code == 401
    assert response.json() == {"error": "credenciales inválidas"}
    assert COOKIE_NAME not in response.cookies


@pytest.mark.asyncio
async def test_login_updates_last_login_at(setup):
    async with _client() as client:
        await client.post(
            "/api/auth/login",
            json={"email": setup["email"], "password": PASSWORD},
        )
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT last_login_at FROM app_user WHERE id = %s",
                (setup["user_id"],),
            )
            (last_login,) = await cur.fetchone()
    assert last_login is not None


@pytest.mark.asyncio
async def test_logout_revokes_session(setup):
    async with _client() as client:
        login_resp = await client.post(
            "/api/auth/login",
            json={"email": setup["email"], "password": PASSWORD},
        )
        cookie_value = login_resp.cookies[COOKIE_NAME]
        client.cookies.set(COOKIE_NAME, cookie_value)
        logout_resp = await client.post("/api/auth/logout")
    assert logout_resp.status_code == 204
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT revoked_at FROM session WHERE id = %s",
                (cookie_value,),
            )
            (revoked,) = await cur.fetchone()
    assert revoked is not None


@pytest.mark.asyncio
async def test_logout_without_cookie_is_idempotent():
    async with _client() as client:
        response = await client.post("/api/auth/logout")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_me_returns_401_after_logout(setup):
    async with _client() as client:
        login_resp = await client.post(
            "/api/auth/login",
            json={"email": setup["email"], "password": PASSWORD},
        )
        cookie_value = login_resp.cookies[COOKIE_NAME]
        client.cookies.set(COOKIE_NAME, cookie_value)
        me_before = await client.get("/api/me")
        await client.post("/api/auth/logout")
        # Re-set the cookie because logout clears it on the client side.
        client.cookies.set(COOKIE_NAME, cookie_value)
        me_after = await client.get("/api/me")
    assert me_before.status_code == 200
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_runs_dummy_verify(monkeypatch, pool_lifecycle):
    from trama import auth_routes

    calls = []

    def spy_verify(plaintext, hashed):
        calls.append((plaintext, hashed))
        return False

    monkeypatch.setattr(auth_routes, "verify_password", spy_verify)
    async with _client() as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "anything"},
        )
    assert response.status_code == 401
    assert response.json() == {"error": "credenciales inválidas"}
    assert len(calls) == 1, (
        "unknown-email path must still run a verify_password against the dummy hash"
    )
