import re

import pytest

from trama import db
from trama.config import settings
from trama.passwords import hash_password
from trama.sessions import COOKIE_NAME

from .conftest import client


@pytest.mark.asyncio
async def test_logout_clear_cookie_mirrors_set_attributes(pool_lifecycle):
    from uuid import uuid4

    cuit = f"00-{uuid4().hex[:8]}-0"
    email = f"test-{uuid4().hex[:8]}@example.com"
    password = "secret"
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
                (node_id, email, hash_password(password)),
            )
            (uid,) = await cur.fetchone()

    try:
        async with client() as c:
            login = await c.post(
                "/api/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200
            logout = await c.post("/api/auth/logout")
        assert logout.status_code == 204
        set_cookie_headers = logout.headers.get_list("set-cookie")
        cookie_str = next(
            (h for h in set_cookie_headers if h.startswith(f"{COOKIE_NAME}=")), None
        )
        assert cookie_str is not None, (
            "logout must emit a Set-Cookie header clearing the session"
        )
        assert re.search(r"\bhttponly\b", cookie_str, re.IGNORECASE)
        assert re.search(r"samesite=lax", cookie_str, re.IGNORECASE)
        if settings.cookie_secure:
            assert re.search(r"\bsecure\b", cookie_str, re.IGNORECASE)
        assert re.search(r"max-age=0", cookie_str, re.IGNORECASE) or "1970" in cookie_str
    finally:
        async with db.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM app_user WHERE id = %s", (uid,))
                await cur.execute("DELETE FROM node WHERE id = %s", (node_id,))
