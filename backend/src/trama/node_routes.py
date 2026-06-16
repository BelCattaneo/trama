from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from trama import db
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
