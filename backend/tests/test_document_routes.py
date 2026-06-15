import hashlib
import io
import zipfile

import pytest
import pytest_asyncio

from trama import db
from trama.sessions import COOKIE_NAME

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
async def setup(node_user):
    yield node_user


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
    doc = body["document"]
    assert doc["original_filename"] == "pedido_enero.xlsx"
    assert (
        doc["mime_type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert doc["size_bytes"] == len(data)
    assert doc["content_hash"] == hashlib.sha256(data).hexdigest()
    assert "storage_ref" not in response.text
    # parse_attempt present for xlsx; fake bytes are invalid → confidence 0
    assert body["parse_attempt"] is not None
    assert body["parse_attempt"]["strategy"] == "deterministic"

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT node_id, original_filename, mime_type, size_bytes
                   FROM document WHERE id = %s""",
                (doc["id"],),
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
    body = response.json()
    assert body["document"]["mime_type"] == "application/pdf"
    assert body["parse_attempt"] is None


@pytest.mark.asyncio
async def test_upload_csv_happy_path(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("lista.csv", CSV_BYTES, "application/octet-stream")},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["document"]["mime_type"] == "text/csv"
    assert body["parse_attempt"] is not None


@pytest.mark.asyncio
async def test_upload_png_happy_path(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("foto.png", PNG_BYTES, "application/octet-stream")},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["document"]["mime_type"] == "image/png"
    assert body["parse_attempt"] is None


@pytest.mark.asyncio
async def test_upload_jpeg_happy_path(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("foto.jpg", JPEG_BYTES, "application/octet-stream")},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["document"]["mime_type"] == "image/jpeg"
    assert body["parse_attempt"] is None


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
async def test_upload_rejects_utf8_text_without_delimiter(setup):
    payload = b"this is plain prose without any csv delimiters at all\nstill prose\n"
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={"file": ("notas.txt", payload, "application/octet-stream")},
        )
    assert response.status_code == 400
    assert response.json() == {"error": "formato no soportado"}


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
        doc1 = r1.json()["document"]
        doc2 = r2.json()["document"]
        assert doc1["id"] != doc2["id"]
        assert doc1["content_hash"] == doc2["content_hash"]

        async with db.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT storage_ref FROM document
                       WHERE node_id = %s AND content_hash = %s""",
                    (setup["node_id"], doc1["content_hash"]),
                )
                rows = await cur.fetchall()
        assert len(rows) == 2
        assert rows[0][0] == rows[1][0]

        prefix = doc1["content_hash"][:2]
        stored = tmp_path / prefix / doc1["content_hash"]
        assert stored.read_bytes() == data
    finally:
        app.state.storage = original_storage
