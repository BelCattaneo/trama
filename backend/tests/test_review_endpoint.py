import json

import pytest
import pytest_asyncio

from trama import db
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user


async def _insert_document(node_id, filename="doc.pdf", mime="application/pdf"):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref)
                   VALUES (%s, %s, %s, 100, %s, 'ab/dummy')
                   RETURNING id""",
                (node_id, filename, mime, "a" * 64),
            )
            (doc_id,) = await cur.fetchone()
    return doc_id


async def _insert_attempt(
    doc_id,
    strategy="deterministic",
    confidence=1.0,
    payload=None,
    prompt_version=None,
    error_message=None,
    is_winner=False,
    created_at_offset_seconds=0,
):
    payload_json = json.dumps(payload) if payload is not None else None
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence,
                                              payload, prompt_version, error_message,
                                              is_winner, created_at)
                   VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s,
                           now() + (%s || ' seconds')::interval)
                   RETURNING id""",
                (
                    doc_id,
                    strategy,
                    confidence,
                    payload_json,
                    prompt_version,
                    error_message,
                    is_winner,
                    created_at_offset_seconds,
                ),
            )
            (attempt_id,) = await cur.fetchone()
    return attempt_id


@pytest_asyncio.fixture
async def setup(node_user):
    yield node_user


@pytest.mark.asyncio
async def test_review_owner_with_single_attempt_returns_200(setup):
    doc_id = await _insert_document(setup["node_id"])
    attempt_id = await _insert_attempt(
        doc_id,
        payload={"lines": [{"product": "x", "quantity": 1.5}], "warnings": []},
        prompt_version="v1",
    )
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/documents/{doc_id}/review")
    assert response.status_code == 200
    body = response.json()
    assert body["document"]["id"] == str(doc_id)
    assert body["document"]["original_filename"] == "doc.pdf"
    assert body["document"]["mime_type"] == "application/pdf"
    assert body["document"]["size_bytes"] == 100
    assert "uploaded_at" in body["document"]
    assert body["parse_attempt"]["id"] == str(attempt_id)
    assert body["parse_attempt"]["strategy"] == "deterministic"
    assert body["parse_attempt"]["confidence"] == 1.0
    assert body["parse_attempt"]["prompt_version"] == "v1"
    assert body["parse_attempt"]["is_winner"] is False
    assert body["parse_attempt"]["error_message"] is None
    assert body["parse_attempt"]["payload"]["lines"][0]["product"] == "x"


@pytest.mark.asyncio
async def test_review_owner_with_multiple_attempts_returns_latest(setup):
    doc_id = await _insert_document(setup["node_id"])
    await _insert_attempt(doc_id, strategy="deterministic", created_at_offset_seconds=-100)
    await _insert_attempt(doc_id, strategy="llm", confidence=0.9, created_at_offset_seconds=-50)
    latest_id = await _insert_attempt(
        doc_id, strategy="llm", confidence=0.5, created_at_offset_seconds=0
    )
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/documents/{doc_id}/review")
    assert response.status_code == 200
    body = response.json()
    assert body["parse_attempt"]["id"] == str(latest_id)
    assert body["parse_attempt"]["confidence"] == 0.5


@pytest.mark.asyncio
async def test_review_non_owner_returns_404(pool_lifecycle):
    a = await make_node_with_user()
    b = await make_node_with_user()
    try:
        doc_id = await _insert_document(b["node_id"])
        await _insert_attempt(doc_id)
        async with client() as c:
            c.cookies.set(COOKIE_NAME, a["session_id"])
            response = await c.get(f"/api/documents/{doc_id}/review")
        assert response.status_code == 404
        assert response.json() == {"error": "documento no encontrado"}
    finally:
        await cleanup_node(a["node_id"], a["user_id"])
        await cleanup_node(b["node_id"], b["user_id"])


@pytest.mark.asyncio
async def test_review_unauthenticated_returns_401(setup):
    doc_id = await _insert_document(setup["node_id"])
    async with client() as c:
        response = await c.get(f"/api/documents/{doc_id}/review")
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}


@pytest.mark.asyncio
async def test_review_document_without_attempt_returns_null(setup):
    doc_id = await _insert_document(setup["node_id"], filename="foto.png", mime="image/png")
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/documents/{doc_id}/review")
    assert response.status_code == 200
    body = response.json()
    assert body["document"]["id"] == str(doc_id)
    assert body["parse_attempt"] is None


@pytest.mark.asyncio
async def test_review_confirmed_document_returns_is_winner_true(setup):
    doc_id = await _insert_document(setup["node_id"])
    await _insert_attempt(doc_id, is_winner=True, confidence=1.0)
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/documents/{doc_id}/review")
    assert response.status_code == 200
    body = response.json()
    assert body["parse_attempt"]["is_winner"] is True
