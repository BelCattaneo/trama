from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID

from fastapi import HTTPException, Request, Response

from trama import db
from trama.config import settings

COOKIE_NAME = "trama_session"
TOKEN_NBYTES = 32


@dataclass
class Session:
    id: str
    user_id: UUID
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


@dataclass
class AuthUser:
    id: UUID
    node_id: UUID
    email: str
    full_name: str | None


async def create_session(user_id: UUID) -> Session:
    session_id = token_urlsafe(TOKEN_NBYTES)
    expires_at = datetime.now(UTC) + timedelta(days=settings.session_ttl_days)
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO session (id, user_id, expires_at)
                VALUES (%s, %s, %s)
                RETURNING id, user_id, created_at, expires_at, revoked_at
                """,
                (session_id, user_id, expires_at),
            )
            row = await cur.fetchone()
    return Session(*row)


async def load_session(session_id: str) -> Session | None:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, created_at, expires_at, revoked_at
                FROM session
                WHERE id = %s
                  AND revoked_at IS NULL
                  AND expires_at > now()
                """,
                (session_id,),
            )
            row = await cur.fetchone()
    return Session(*row) if row else None


async def revoke_session(session_id: str) -> None:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE session SET revoked_at = now() WHERE id = %s",
                (session_id,),
            )


async def current_user(request: Request) -> AuthUser | None:
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None
    session = await load_session(cookie)
    if session is None:
        return None
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, node_id, email, full_name FROM app_user WHERE id = %s",
                (session.user_id,),
            )
            row = await cur.fetchone()
    return AuthUser(*row) if row else None


async def require_user(request: Request) -> AuthUser:
    user = await current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="no autenticado")
    return user


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        session_id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 86400,
    )


def clear_session_cookie(response: Response) -> None:
    # delete_cookie must mirror set_cookie's attributes or browsers may not match
    # the cookie and the deletion silently no-ops.
    response.delete_cookie(
        COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
