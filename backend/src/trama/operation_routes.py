from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from trama import db
from trama.sessions import AuthUser, require_user


class OperationListItem(BaseModel):
    id: UUID
    kind: str
    operation_date: date
    confirmed_at: datetime
    line_count: int


class OperationListResponse(BaseModel):
    items: list[OperationListItem]
    total: int


class OperationLineOut(BaseModel):
    line_no: int
    product: str
    quantity: float
    unit: str | None = None


class OperationDetailResponse(BaseModel):
    id: UUID
    kind: str
    operation_date: date
    confirmed_at: datetime
    lines: list[OperationLineOut]


router = APIRouter(prefix="/api")


@router.get("/operations", response_model=OperationListResponse)
async def list_operations(
    user: Annotated[AuthUser, Depends(require_user)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OperationListResponse:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT o.id, o.kind, o.operation_date, o.confirmed_at,
                          (SELECT COUNT(*) FROM operation_line ol
                           WHERE ol.operation_id = o.id) AS line_count
                   FROM operation o
                   WHERE o.node_id = %s
                   ORDER BY o.confirmed_at DESC
                   LIMIT %s OFFSET %s""",
                (user.node_id, limit, offset),
            )
            rows = await cur.fetchall()

            await cur.execute(
                "SELECT COUNT(*) FROM operation WHERE node_id = %s",
                (user.node_id,),
            )
            (total,) = await cur.fetchone()

    items = [
        OperationListItem(
            id=r[0],
            kind=r[1],
            operation_date=r[2],
            confirmed_at=r[3],
            line_count=r[4],
        )
        for r in rows
    ]
    return OperationListResponse(items=items, total=total)


@router.get("/operations/{operation_id}", response_model=OperationDetailResponse)
async def get_operation(
    operation_id: UUID,
    user: Annotated[AuthUser, Depends(require_user)],
) -> OperationDetailResponse:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, kind, operation_date, confirmed_at
                   FROM operation
                   WHERE id = %s AND node_id = %s""",
                (operation_id, user.node_id),
            )
            row = await cur.fetchone()
            if row is None:
                raise HTTPException(
                    status_code=404, detail="operación no encontrada"
                )
            op_id, kind, operation_date, confirmed_at = row

            await cur.execute(
                """SELECT line_no, product, quantity, unit
                   FROM operation_line
                   WHERE operation_id = %s
                   ORDER BY line_no ASC""",
                (op_id,),
            )
            line_rows = await cur.fetchall()

    lines = [
        OperationLineOut(
            line_no=lr[0],
            product=lr[1],
            quantity=float(lr[2]),
            unit=lr[3],
        )
        for lr in line_rows
    ]
    return OperationDetailResponse(
        id=op_id,
        kind=kind,
        operation_date=operation_date,
        confirmed_at=confirmed_at,
        lines=lines,
    )
