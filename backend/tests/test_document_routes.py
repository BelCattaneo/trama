import hashlib
import io
import zipfile
from uuid import uuid4

import pytest
import pytest_asyncio

from trama import db
from trama.sessions import COOKIE_NAME, create_session

from .conftest import client


def make_xlsx_bytes(payload: bytes = b"<xml/>") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("xl/workbook.xml", payload)
    return buf.getvalue()


PDF_BYTES = b"%PDF-1.4\n%fake pdf body\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
CSV_BYTES = b"name,qty\napple,3\nbanana,5\n"
HEIC_BYTES = b"\x00\x00\x00\x20ftypheic\x00" * 4


@pytest_asyncio.fixture
async def setup(pool_lifecycle):
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
    yield {
        "user_id": uid,
        "node_id": node_id,
        "session_id": session.id,
    }
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM document WHERE node_id = %s", (node_id,)
            )
            await cur.execute("DELETE FROM app_user WHERE id = %s", (uid,))
            await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))


@pytest.mark.asyncio
async def test_upload_xlsx_happy_path(setup):
    data = make_xlsx_bytes()
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={
                "file": (
                    "pedido_enero.xlsx",
                    data,
                    "application/octet-stream",
                )
            },
        )
    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "pedido_enero.xlsx"
    assert (
        body["mime_type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert body["size_bytes"] == len(data)
    assert body["content_hash"] == hashlib.sha256(data).hexdigest()
    assert "storage_ref" not in body
    assert "storage_ref" not in response.text

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT node_id, original_filename, mime_type, size_bytes
                   FROM document WHERE id = %s""",
                (body["id"],),
            )
            row = await cur.fetchone()
    assert row[0] == setup["node_id"]
    assert row[1] == "pedido_enero.xlsx"
    assert row[3] == len(data)


@pytest.mark.asyncio
async def test_upload_pdf_happy_path(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("doc.pdf", PDF_BYTES, "application/octet-stream")},
        )
    assert response.status_code == 201
    assert response.json()["mime_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_upload_csv_happy_path(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("lista.csv", CSV_BYTES, "application/octet-stream")},
        )
    assert response.status_code == 201
    assert response.json()["mime_type"] == "text/csv"


@pytest.mark.asyncio
async def test_upload_png_happy_path(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("foto.png", PNG_BYTES, "application/octet-stream")},
        )
    assert response.status_code == 201
    assert response.json()["mime_type"] == "image/png"


@pytest.mark.asyncio
async def test_upload_jpeg_happy_path(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("foto.jpg", JPEG_BYTES, "application/octet-stream")},
        )
    assert response.status_code == 201
    assert response.json()["mime_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_upload_unauthenticated_no_cookie(pool_lifecycle):
    async with client() as c:
        response = await c.post(
            "/api/documents",
            files={"file": ("x.pdf", PDF_BYTES, "application/octet-stream")},
        )
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_mime(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("x.heic", HEIC_BYTES, "application/octet-stream")},
        )
    assert response.status_code == 400
    assert response.json() == {"error": "formato no soportado"}

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM document WHERE node_id = %s",
                (setup["node_id"],),
            )
            (count,) = await cur.fetchone()
    assert count == 0


@pytest.mark.asyncio
async def test_upload_rejects_oversize(setup):
    big = b"%PDF-" + b"x" * (10 * 1024 * 1024)
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("big.pdf", big, "application/octet-stream")},
        )
    assert response.status_code == 400
    assert response.json() == {"error": "archivo demasiado grande"}


@pytest.mark.asyncio
async def test_upload_accepts_exactly_10mb(setup):
    base = b"%PDF-"
    payload = base + b"x" * (10 * 1024 * 1024 - len(base))
    assert len(payload) == 10 * 1024 * 1024
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("limit.pdf", payload, "application/octet-stream")},
        )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_upload_rejects_empty(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("empty.pdf", b"", "application/octet-stream")},
        )
    assert response.status_code == 400
    assert response.json() == {"error": "archivo vacío"}


@pytest.mark.asyncio
async def test_duplicate_upload_two_rows_one_physical_file(setup, tmp_path):
    from trama.main import app
    from trama.storage import LocalStorage

    original_storage = app.state.storage
    app.state.storage = LocalStorage(tmp_path)
    try:
        data = make_xlsx_bytes()
        async with client() as c:
            c.cookies.set(COOKIE_NAME, setup["session_id"])
            r1 = await c.post(
                "/api/documents",
                files={"file": ("a.xlsx", data, "application/octet-stream")},
            )
            r2 = await c.post(
                "/api/documents",
                files={"file": ("b.xlsx", data, "application/octet-stream")},
            )
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] != r2.json()["id"]
        assert r1.json()["content_hash"] == r2.json()["content_hash"]

        async with db.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT storage_ref FROM document
                       WHERE node_id = %s AND content_hash = %s""",
                    (setup["node_id"], r1.json()["content_hash"]),
                )
                rows = await cur.fetchall()
        assert len(rows) == 2
        assert rows[0][0] == rows[1][0]

        prefix = r1.json()["content_hash"][:2]
        stored = tmp_path / prefix / r1.json()["content_hash"]
        assert stored.read_bytes() == data
    finally:
        app.state.storage = original_storage
