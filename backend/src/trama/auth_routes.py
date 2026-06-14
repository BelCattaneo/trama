from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from trama import db
from trama.passwords import hash_password, verify_password
from trama.sessions import (
    COOKIE_NAME,
    clear_session_cookie,
    create_session,
    revoke_session,
    set_session_cookie,
)


class LoginRequest(BaseModel):
    email: str
    password: str


# Used to keep the failure-path latency comparable when the email is unknown.
_DUMMY_HASH = hash_password("dummy-placeholder-for-timing")

router = APIRouter(prefix="/api/auth")


# TODO(post-MVP): rate-limit /login to slow brute-force attempts.
@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, password_hash FROM app_user WHERE email = %s",
                (payload.email,),
            )
            row = await cur.fetchone()

    if row is None:
        verify_password(payload.password, _DUMMY_HASH)
        return JSONResponse({"error": "credenciales inválidas"}, status_code=401)

    user_id, password_hash = row
    if not verify_password(payload.password, password_hash):
        return JSONResponse({"error": "credenciales inválidas"}, status_code=401)

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE app_user SET last_login_at = now() WHERE id = %s",
                (user_id,),
            )

    session = await create_session(user_id)
    set_session_cookie(response, session.id)
    return {"ok": True}


@router.post("/logout", status_code=204)
async def logout(request: Request):
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        await revoke_session(cookie)
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response
