from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from trama import db
from trama.sessions import AuthUser, require_user


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    last_login_at: datetime | None


class NodeOut(BaseModel):
    id: UUID
    cuit: str
    display_name: str
    role: str
    address_text: str | None
    latitude: float
    longitude: float
    zone_label: str | None


class MeResponse(BaseModel):
    user: UserOut
    node: NodeOut


router = APIRouter(prefix="/api")


@router.get("/me", response_model=MeResponse)
async def get_me(user: Annotated[AuthUser, Depends(require_user)]):
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, email, full_name, last_login_at FROM app_user WHERE id = %s",
                (user.id,),
            )
            urow = await cur.fetchone()
            await cur.execute(
                """SELECT id, cuit, display_name, role, address_text,
                          latitude, longitude, zone_label
                   FROM node WHERE id = %s""",
                (user.node_id,),
            )
            nrow = await cur.fetchone()
    return MeResponse(
        user=UserOut(id=urow[0], email=urow[1], full_name=urow[2], last_login_at=urow[3]),
        node=NodeOut(
            id=nrow[0],
            cuit=nrow[1],
            display_name=nrow[2],
            role=nrow[3],
            address_text=nrow[4],
            latitude=nrow[5],
            longitude=nrow[6],
            zone_label=nrow[7],
        ),
    )
