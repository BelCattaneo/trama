from typing import Literal

import psycopg
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator

from trama import db
from trama.cuit import validate_cuit
from trama.geocode import geocode
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


class SignupRequest(BaseModel):
    cuit: str
    display_name: str
    role: Literal["consumer", "producer", "both"]
    email: str
    password: str
    full_name: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @model_validator(mode="after")
    def must_have_location(self):
        has_address = self.address is not None and self.address.strip() != ""
        has_coords = self.latitude is not None and self.longitude is not None
        if not (has_address or has_coords):
            raise ValueError("either address or latitude+longitude must be provided")
        return self


# Used to keep the failure-path latency comparable when the email is unknown.
_DUMMY_HASH = hash_password("dummy-placeholder-for-timing")

router = APIRouter(prefix="/api/auth")


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


@router.post("/signup", status_code=201)
async def signup(payload: SignupRequest, response: Response):
    if not validate_cuit(payload.cuit):
        return JSONResponse({"error": "CUIT inválido"}, status_code=400)

    if payload.latitude is not None and payload.longitude is not None:
        latitude, longitude, zone_label = payload.latitude, payload.longitude, None
    else:
        result = await geocode(payload.address)
        if result is None:
            return JSONResponse(
                {"error": "no se pudo ubicar la dirección, ingresá coordenadas manualmente"},
                status_code=400,
            )
        latitude, longitude, zone_label = result.latitude, result.longitude, result.zone_label

    password_hash = hash_password(payload.password)

    try:
        async with db.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO node (cuit, display_name, role,
                                      address_text, latitude, longitude, zone_label)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        payload.cuit,
                        payload.display_name,
                        payload.role,
                        payload.address,
                        latitude,
                        longitude,
                        zone_label,
                    ),
                )
                (node_id,) = await cur.fetchone()
                await cur.execute(
                    """
                    INSERT INTO app_user (node_id, email, password_hash, full_name)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (node_id, payload.email, password_hash, payload.full_name),
                )
                (user_id,) = await cur.fetchone()
    except psycopg.errors.UniqueViolation as exc:
        constraint = (exc.diag.constraint_name or "") if exc.diag else ""
        if "cuit" in constraint:
            return JSONResponse({"error": "CUIT ya registrado"}, status_code=409)
        if "email" in constraint:
            return JSONResponse({"error": "email ya registrado"}, status_code=409)
        raise

    session = await create_session(user_id)
    set_session_cookie(response, session.id)
    return {"node_id": str(node_id), "user_id": str(user_id)}
