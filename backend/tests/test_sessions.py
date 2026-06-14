from uuid import uuid4

import pytest
import pytest_asyncio

from trama import db
from trama.config import settings
from trama.sessions import create_session, load_session, revoke_session


@pytest_asyncio.fixture
async def pool_lifecycle():
    await db.open_pool(settings.database_url, settings.pool_min, settings.pool_max)
    yield
    await db.close_pool()


@pytest_asyncio.fixture
async def user_id(pool_lifecycle):
    cuit = f"00-{uuid4().hex[:8]}-0"
    email = f"test-{uuid4().hex[:8]}@example.com"
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO node (cuit, display_name, role, latitude, longitude)
                VALUES (%s, 'Test Node', 'consumer', 0, 0)
                RETURNING id
                """,
                (cuit,),
            )
            (node_id,) = await cur.fetchone()
            await cur.execute(
                """
                INSERT INTO app_user (node_id, email, password_hash)
                VALUES (%s, %s, 'unused')
                RETURNING id
                """,
                (node_id, email),
            )
            (uid,) = await cur.fetchone()
    yield uid
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM app_user WHERE id = %s", (uid,))
            await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))


@pytest.mark.asyncio
async def test_create_then_load(user_id):
    session = await create_session(user_id)
    loaded = await load_session(session.id)
    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.user_id == user_id


@pytest.mark.asyncio
async def test_unknown_session_returns_none(pool_lifecycle):
    assert await load_session("nonexistent-session-id") is None


@pytest.mark.asyncio
async def test_revoked_session_not_loaded(user_id):
    session = await create_session(user_id)
    await revoke_session(session.id)
    assert await load_session(session.id) is None


@pytest.mark.asyncio
async def test_expired_session_not_loaded(user_id):
    session = await create_session(user_id)
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE session SET expires_at = now() - interval '1 hour' WHERE id = %s",
                (session.id,),
            )
    assert await load_session(session.id) is None


@pytest.mark.asyncio
async def test_session_id_is_url_safe_token(user_id):
    session = await create_session(user_id)
    # secrets.token_urlsafe(32) produces 43 url-safe chars (no padding).
    assert len(session.id) >= 40
    assert all(c.isalnum() or c in "-_" for c in session.id)
