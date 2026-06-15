from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from trama import db
from trama.sessions import AuthUser, require_user

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class OperationListItem(BaseModel):
    id: UUID
    kind: str
    operation_date: date
    confirmed_at: datetime
    line_count: int


class OperationsListResponse(BaseModel):
    items: list[OperationListItem]
    total: int


class OperationLineOut(BaseModel):
    line_no: int
    product: str
    quantity: float
    unit: str | None
    page: int | None


class OperationDetailOut(BaseModel):
    id: UUID
    kind: str
    operation_date: date
    confirmed_at: datetime
    document_id: UUID
    lines: list[OperationLineOut]


router = APIRouter(prefix="/api")


@router.get("/operations", response_model=OperationsListResponse)
async def list_operations(
    user: Annotated[AuthUser, Depends(require_user)],
    limit: int = Query(DEFAULT_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
) -> OperationsListResponse:
    capped_limit = min(limit, MAX_LIMIT)
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT o.id, o.kind, o.operation_date, o.confirmed_at,
                          COUNT(ol.id) AS line_count
                   FROM operation o
                   LEFT JOIN operation_line ol ON ol.operation_id = o.id
                   WHERE o.node_id = %s
                   GROUP BY o.id
                   ORDER BY o.confirmed_at DESC, o.id DESC
                   LIMIT %s OFFSET %s""",
                (user.node_id, capped_limit, offset),
            )
            rows = await cur.fetchall()
            await cur.execute(
                "SELECT COUNT(*) FROM operation WHERE node_id = %s",
                (user.node_id,),
            )
            (total,) = await cur.fetchone()
    return OperationsListResponse(
        items=[
            OperationListItem(
                id=r[0],
                kind=r[1],
                operation_date=r[2],
                confirmed_at=r[3],
                line_count=r[4],
            )
            for r in rows
        ],
        total=total,
    )


@router.get("/operations/{operation_id}", response_model=OperationDetailOut)
async def get_operation(
    operation_id: UUID,
    user: Annotated[AuthUser, Depends(require_user)],
) -> OperationDetailOut:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT o.id, o.kind, o.operation_date, o.confirmed_at,
                          pa.document_id
                   FROM operation o
                   JOIN parse_attempt pa ON pa.id = o.parse_attempt_id
                   WHERE o.id = %s AND o.node_id = %s""",
                (operation_id, user.node_id),
            )
            op_row = await cur.fetchone()
            if op_row is None:
                raise HTTPException(
                    status_code=404, detail="operación no encontrada"
                )
            await cur.execute(
                """SELECT line_no, product, quantity, unit, page
                   FROM operation_line
                   WHERE operation_id = %s
                   ORDER BY line_no ASC""",
                (operation_id,),
            )
            line_rows = await cur.fetchall()

    return OperationDetailOut(
        id=op_row[0],
        kind=op_row[1],
        operation_date=op_row[2],
        confirmed_at=op_row[3],
        document_id=op_row[4],
        lines=[
            OperationLineOut(
                line_no=r[0],
                product=r[1],
                quantity=float(r[2]),
                unit=r[3],
                page=r[4],
            )
            for r in line_rows
        ],
    )
