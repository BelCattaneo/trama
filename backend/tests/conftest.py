from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

from trama import db
from trama.config import settings
from trama.main import app
from trama.sessions import create_session
from trama.storage import LocalStorage


class _StubLLMClient:
    async def parse_image(self, image_bytes: bytes, prompt: str) -> dict:
        return {
            "text": '{"lines": [], "warnings": []}',
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "response_id": None,
        }


@pytest.fixture(autouse=True)
def _llm_stub(monkeypatch):
    monkeypatch.setattr(
        "trama.parsing.orchestrator.get_llm_client", lambda: _StubLLMClient()
    )


@pytest.fixture(autouse=True, scope="session")
def _isolated_storage(tmp_path_factory):
    original = getattr(app.state, "storage", None)
    app.state.storage = LocalStorage(tmp_path_factory.mktemp("storage"))
    yield
    if original is None:
        del app.state.storage
    else:
        app.state.storage = original


@pytest_asyncio.fixture
async def pool_lifecycle():
    await db.open_pool(settings.database_url, settings.pool_min, settings.pool_max)
    yield
    await db.close_pool()


def client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def make_node_with_user(
    *,
    role: str = "consumer",
    display_name: str = "Test Node",
    full_name: str = "Test User",
    zone_label: str | None = None,
    address_text: str | None = None,
) -> dict:
    cuit = f"00-{uuid4().hex[:8]}-0"
    email = f"test-{uuid4().hex[:8]}@example.com"
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO node (cuit, display_name, role, latitude, longitude,
                                     address_text, zone_label)
                   VALUES (%s, %s, %s, -34.6, -58.4, %s, %s)
                   RETURNING id""",
                (cuit, display_name, role, address_text, zone_label),
            )
            (node_id,) = await cur.fetchone()
            await cur.execute(
                """INSERT INTO app_user (node_id, email, password_hash, full_name)
                   VALUES (%s, %s, 'never-exposed-hash', %s)
                   RETURNING id""",
                (node_id, email, full_name),
            )
            (uid,) = await cur.fetchone()
    session = await create_session(uid)
    return {
        "user_id": uid,
        "node_id": node_id,
        "session_id": session.id,
        "email": email,
        "cuit": cuit,
    }


async def cleanup_node(node_id, user_id) -> None:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM operation WHERE node_id = %s", (node_id,)
            )
            await cur.execute(
                "DELETE FROM document WHERE node_id = %s", (node_id,)
            )
            await cur.execute("DELETE FROM app_user WHERE id = %s", (user_id,))
            await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))


@pytest_asyncio.fixture
async def node_user(pool_lifecycle):
    """Create a node + user + session, yield it, then cascade-clean."""
    data = await make_node_with_user()
    yield data
    await cleanup_node(data["node_id"], data["user_id"])
