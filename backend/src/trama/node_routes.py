from typing import Annotated, Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from trama import db
from trama.cuit import validate_cuit
from trama.geocode import geocode
from trama.rate_limit import rate_limit_upload
from trama.sessions import AuthUser, require_user

PRODUCER_LIST_LIMIT = 100


class ProducerListItem(BaseModel):
    id: UUID
    display_name: str
    cuit: str
    role: str
    zone_label: str | None


class ProducersListResponse(BaseModel):
    producers: list[ProducerListItem]


class CreateNodeBody(BaseModel):
    cuit: str
    display_name: str
    address: str
    role: Literal["producer", "both"]


router = APIRouter(prefix="/api")


@router.get("/producers", response_model=ProducersListResponse)
async def list_producers(
    user: Annotated[AuthUser, Depends(require_user)],
    q: str | None = None,
) -> ProducersListResponse:
    q_like = f"%{q}%" if q else None
    async with db.cursor() as cur:
        await cur.execute(
            """SELECT id, display_name, cuit, role, zone_label
               FROM node
               WHERE role IN ('producer', 'both')
                 AND (%(q)s::text IS NULL
                      OR display_name ILIKE %(q_like)s
                      OR cuit ILIKE %(q_like)s)
               ORDER BY display_name
               LIMIT %(limit)s""",
            {"q": q, "q_like": q_like, "limit": PRODUCER_LIST_LIMIT},
        )
        rows = await cur.fetchall()
    return ProducersListResponse(
        producers=[
            ProducerListItem(
                id=row[0],
                display_name=row[1],
                cuit=row[2],
                role=row[3],
                zone_label=row[4],
            )
            for row in rows
        ]
    )


@router.post("/nodes", status_code=201, response_model=ProducerListItem)
async def create_node(
    body: CreateNodeBody,
    _user: Annotated[AuthUser, Depends(rate_limit_upload)],
) -> ProducerListItem | JSONResponse:
    if not validate_cuit(body.cuit):
        return JSONResponse({"error": "CUIT inválido"}, status_code=400)

    result = await geocode(body.address)
    if result is None:
        return JSONResponse(
            {"error": "no pudimos ubicar la dirección"}, status_code=400
        )

    try:
        async with db.cursor() as cur:
            await cur.execute(
                """INSERT INTO node (cuit, display_name, role, address_text,
                                     latitude, longitude, zone_label)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING id, display_name, cuit, role, zone_label""",
                (
                    body.cuit,
                    body.display_name,
                    body.role,
                    body.address,
                    result.latitude,
                    result.longitude,
                    result.zone_label,
                ),
            )
            row = await cur.fetchone()
    except psycopg.errors.UniqueViolation as exc:
        constraint = (exc.diag.constraint_name or "") if exc.diag else ""
        if "cuit" in constraint:
            return JSONResponse(
                {"error": "CUIT ya registrado"}, status_code=409
            )
        raise

    return ProducerListItem(
        id=row[0],
        display_name=row[1],
        cuit=row[2],
        role=row[3],
        zone_label=row[4],
    )
