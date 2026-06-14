from uuid import uuid4

import pytest
import pytest_asyncio

from trama import db
from trama.sessions import COOKIE_NAME, create_session

from .conftest import client


async def _make_node_with_user():
    cuit = f"00-{uuid4().hex[:8]}-0"
    email = f"test-{uuid4().hex[:8]}@example.com"
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO node (cuit, display_name, role, latitude, longitude)
                   VALUES (%s, 'Test Node', 'consumer', -34.6, -58.4)
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
    return {"node_id": node_id, "user_id": uid, "session_id": session.id}


async def _cleanup_node(node_id, user_id):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM document WHERE node_id = %s", (node_id,)
            )
            await cur.execute("DELETE FROM app_user WHERE id = %s", (user_id,))
            await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))


async def _insert_document(node_id, filename, mime, uploaded_at_offset_seconds=0):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref,
                                         uploaded_at)
                   VALUES (%s, %s, %s, 100,
                           %s, 'ab/dummy',
                           now() + (%s || ' seconds')::interval)""",
                (node_id, filename, mime, "a" * 64, uploaded_at_offset_seconds),
            )


@pytest_asyncio.fixture
async def setup(pool_lifecycle):
    data = await _make_node_with_user()
    yield data
    await _cleanup_node(data["node_id"], data["user_id"])


@pytest.mark.asyncio
async def test_list_empty(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/documents")
    assert response.status_code == 200
    assert response.json() == {"documents": []}


@pytest.mark.asyncio
async def test_list_three_documents_newest_first(setup):
    await _insert_document(setup["node_id"], "old.pdf", "application/pdf", -100)
    await _insert_document(setup["node_id"], "mid.pdf", "application/pdf", -50)
    await _insert_document(setup["node_id"], "new.pdf", "application/pdf", 0)
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/documents")
    assert response.status_code == 200
    docs = response.json()["documents"]
    assert len(docs) == 3
    assert docs[0]["original_filename"] == "new.pdf"
    assert docs[1]["original_filename"] == "mid.pdf"
    assert docs[2]["original_filename"] == "old.pdf"
    assert "storage_ref" not in response.text


@pytest.mark.asyncio
async def test_list_unauthenticated_no_cookie(pool_lifecycle):
    async with client() as c:
        response = await c.get("/api/documents")
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}


@pytest.mark.asyncio
async def test_list_unauthenticated_response_body_has_no_documents_key(
    pool_lifecycle,
):
    async with client() as c:
        response = await c.get("/api/documents")
    assert "documents" not in response.json()


@pytest.mark.asyncio
async def test_node_isolation_user_a_cannot_see_user_b_documents(pool_lifecycle):
    a = await _make_node_with_user()
    b = await _make_node_with_user()
    try:
        await _insert_document(b["node_id"], "b1.pdf", "application/pdf")
        await _insert_document(b["node_id"], "b2.pdf", "application/pdf")
        async with client() as c:
            c.cookies.set(COOKIE_NAME, a["session_id"])
            response = await c.get("/api/documents")
        assert response.status_code == 200
        assert response.json() == {"documents": []}
    finally:
        await _cleanup_node(a["node_id"], a["user_id"])
        await _cleanup_node(b["node_id"], b["user_id"])
