from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from trama import db
from trama.sessions import AuthUser, require_user

router = APIRouter(prefix="/api")


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
