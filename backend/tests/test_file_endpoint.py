import hashlib
from urllib.parse import quote

import pytest
import pytest_asyncio

from trama import db
from trama.main import app
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user

PDF_BYTES = b"%PDF-1.4\n%fake pdf body\n" + b"\x00" * 64


async def _insert_real_document(
    node_id, *, filename: str, mime: str, contents: bytes
) -> str:
    """Insert a document row and physically store its bytes. Returns the document id."""
    content_hash = hashlib.sha256(contents).hexdigest()
    storage_ref = app.state.storage.save(contents, content_hash)
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (node_id, filename, mime, len(contents), content_hash, storage_ref),
            )
            (doc_id,) = await cur.fetchone()
    return str(doc_id)


async def _insert_document_with_ref(
    node_id, *, filename: str, mime: str, storage_ref: str, size_bytes: int = 100
) -> str:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (node_id, filename, mime, size_bytes, "a" * 64, storage_ref),
            )
            (doc_id,) = await cur.fetchone()
    return str(doc_id)


@pytest_asyncio.fixture
async def setup(node_user):
    yield node_user


@pytest.mark.asyncio
async def test_owner_gets_bytes_with_correct_headers(setup):
    doc_id = await _insert_real_document(
        setup["node_id"],
        filename="pedido.pdf",
        mime="application/pdf",
        contents=PDF_BYTES,
    )
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/documents/{doc_id}/file")
    assert response.status_code == 200
    assert response.content == PDF_BYTES
    assert len(response.content) == len(PDF_BYTES)
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'inline; filename="pedido.pdf"'
    assert response.headers["cache-control"] == "private, max-age=300"


@pytest.mark.asyncio
async def test_owner_gets_non_ascii_filename_rfc5987_encoded(setup):
    filename = "pedido áéíóú ñ.pdf"
    doc_id = await _insert_real_document(
        setup["node_id"],
        filename=filename,
        mime="application/pdf",
        contents=PDF_BYTES,
    )
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/documents/{doc_id}/file")
    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert disposition == f"inline; filename*=UTF-8''{quote(filename, safe='')}"


@pytest.mark.asyncio
async def test_non_owner_gets_404(pool_lifecycle):
    owner = await make_node_with_user()
    intruder = await make_node_with_user()
    try:
        doc_id = await _insert_real_document(
            owner["node_id"],
            filename="private.pdf",
            mime="application/pdf",
            contents=PDF_BYTES,
        )
        async with client() as c:
            c.cookies.set(COOKIE_NAME, intruder["session_id"])
            response = await c.get(f"/api/documents/{doc_id}/file")
        assert response.status_code == 404
        assert response.json() == {"error": "documento no encontrado"}
    finally:
        await cleanup_node(owner["node_id"], owner["user_id"])
        await cleanup_node(intruder["node_id"], intruder["user_id"])


@pytest.mark.asyncio
async def test_unauthenticated_gets_401(pool_lifecycle):
    async with client() as c:
        response = await c.get(
            "/api/documents/00000000-0000-0000-0000-000000000000/file"
        )
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}


@pytest.mark.asyncio
async def test_missing_file_returns_generic_500_without_leaking_path(setup):
    storage_ref = "ff/" + "f" * 64
    doc_id = await _insert_document_with_ref(
        setup["node_id"],
        filename="ghost.pdf",
        mime="application/pdf",
        storage_ref=storage_ref,
    )
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get(f"/api/documents/{doc_id}/file")
    assert response.status_code == 500
    body = response.json()
    assert body == {"error": "no se pudo leer el archivo"}
    assert storage_ref not in response.text
    assert "f" * 64 not in response.text
