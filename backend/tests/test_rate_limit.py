import hashlib
import io
import zipfile

import pytest
import pytest_asyncio

from trama import db, rate_limit
from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user


def _xlsx_bytes(payload: bytes = b"<xml/>") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("xl/workbook.xml", payload)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _fresh_limiters():
    rate_limit._upload_limiter.reset()
    rate_limit._reparse_limiter.reset()
    yield
    rate_limit._upload_limiter.reset()
    rate_limit._reparse_limiter.reset()


@pytest_asyncio.fixture
async def setup(node_user):
    yield node_user


@pytest_asyncio.fixture
async def two_users(pool_lifecycle):
    a = await make_node_with_user(display_name="user a")
    b = await make_node_with_user(display_name="user b")
    yield a, b
    await cleanup_node(a["node_id"], a["user_id"])
    await cleanup_node(b["node_id"], b["user_id"])


async def _seed_document(node_id, mime: str = "text/csv") -> str:
    contents = b"name,qty\napple,1\n"
    content_hash = hashlib.sha256(contents).hexdigest()
    from trama.main import app

    storage = app.state.storage
    storage_ref = storage.save(contents, content_hash)
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document
                       (node_id, original_filename, mime_type,
                        size_bytes, content_hash, storage_ref)
                   VALUES (%s, 'seed.csv', %s, %s, %s, %s)
                   RETURNING id""",
                (node_id, mime, len(contents), content_hash, storage_ref),
            )
            (doc_id,) = await cur.fetchone()
    return str(doc_id)


@pytest.mark.asyncio
async def test_upload_burst_5_ok_6th_429(setup):
    data = _xlsx_bytes()
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        for i in range(rate_limit.UPLOAD_PER_MINUTE):
            r = await c.post(
                "/api/documents",
                files={"file": (f"a{i}.xlsx", data, "application/octet-stream")},
            )
            assert r.status_code == 201, (i, r.text)
        r = await c.post(
            "/api/documents",
            files={"file": ("over.xlsx", data, "application/octet-stream")},
        )
    assert r.status_code == 429
    assert r.json() == {"error": "demasiadas solicitudes, esperá un momento"}


@pytest.mark.asyncio
async def test_reparse_burst_10_ok_11th_429(setup):
    doc_id = await _seed_document(setup["node_id"])
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        for i in range(rate_limit.REPARSE_PER_MINUTE):
            r = await c.post(f"/api/documents/{doc_id}/reparse")
            assert r.status_code == 200, (i, r.text)
        r = await c.post(f"/api/documents/{doc_id}/reparse")
    assert r.status_code == 429
    assert r.json() == {"error": "demasiadas solicitudes, esperá un momento"}


@pytest.mark.asyncio
async def test_refill_after_time_advances(setup, monkeypatch):
    fake_now = [1000.0]

    def _now():
        return fake_now[0]

    monkeypatch.setattr(rate_limit, "_now", _now)
    rate_limit._upload_limiter.reset()

    data = _xlsx_bytes()
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        for i in range(rate_limit.UPLOAD_PER_MINUTE):
            r = await c.post(
                "/api/documents",
                files={"file": (f"a{i}.xlsx", data, "application/octet-stream")},
            )
            assert r.status_code == 201
        r = await c.post(
            "/api/documents",
            files={"file": ("blocked.xlsx", data, "application/octet-stream")},
        )
        assert r.status_code == 429

        # 60 seconds → full refill back to capacity
        fake_now[0] += 60.0
        r = await c.post(
            "/api/documents",
            files={"file": ("after.xlsx", data, "application/octet-stream")},
        )
    assert r.status_code == 201


@pytest.mark.asyncio
async def test_buckets_are_per_user(two_users):
    user_a, user_b = two_users
    data = _xlsx_bytes()
    async with client() as c:
        c.cookies.set(COOKIE_NAME, user_a["session_id"])
        for i in range(rate_limit.UPLOAD_PER_MINUTE):
            r = await c.post(
                "/api/documents",
                files={"file": (f"a{i}.xlsx", data, "application/octet-stream")},
            )
            assert r.status_code == 201
        r = await c.post(
            "/api/documents",
            files={"file": ("over.xlsx", data, "application/octet-stream")},
        )
        assert r.status_code == 429

        c.cookies.set(COOKIE_NAME, user_b["session_id"])
        r = await c.post(
            "/api/documents",
            files={"file": ("b0.xlsx", data, "application/octet-stream")},
        )
    assert r.status_code == 201


@pytest.mark.asyncio
async def test_login_and_signup_are_not_rate_limited(pool_lifecycle):
    async with client() as c:
        # 20 bad logins should all answer with the route's own auth error,
        # never with the rate-limit 429.
        for _ in range(20):
            r = await c.post(
                "/api/auth/login",
                json={"email": "nobody@example.com", "password": "wrong"},
            )
            assert r.status_code != 429
        for _ in range(20):
            r = await c.post(
                "/api/auth/signup",
                json={
                    "email": "nobody@example.com",
                    "password": "x",
                    "cuit": "00-00000000-0",
                    "display_name": "x",
                    "role": "consumer",
                },
            )
            assert r.status_code != 429
