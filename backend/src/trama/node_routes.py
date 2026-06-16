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
TOP_PRODUCTS_LIMIT = 3


class ProducerListItem(BaseModel):
    id: UUID
    display_name: str
    cuit: str | None
    role: str
    zone_label: str | None


class ProducersListResponse(BaseModel):
    producers: list[ProducerListItem]


class CreateNodeBody(BaseModel):
    cuit: str | None = None
    display_name: str
    address: str
    role: Literal["producer", "both"]


class MapNodeOut(BaseModel):
    id: UUID
    display_name: str
    role: str
    latitude: float
    longitude: float
    zone_label: str | None
    orders_last_week: int
    orders_total: int
    top_products: list[str]


class MapResponse(BaseModel):
    nodes: list[MapNodeOut]


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


@router.get("/map", response_model=MapResponse)
async def get_map(
    user: Annotated[AuthUser, Depends(require_user)],
) -> MapResponse:
    async with db.cursor() as cur:
        await cur.execute(
            """WITH order_stats AS (
                   SELECT supplier_node_id AS node_id,
                          COUNT(*) FILTER (
                              WHERE confirmed_at >= now() - interval '7 days'
                          ) AS orders_last_week,
                          COUNT(*) AS orders_total
                   FROM operation
                   WHERE supplier_node_id IS NOT NULL
                   GROUP BY supplier_node_id
               ),
               product_ops AS (
                   SELECT o.supplier_node_id AS node_id,
                          ol.product,
                          COUNT(DISTINCT o.id) AS op_count
                   FROM operation o
                   JOIN operation_line ol ON ol.operation_id = o.id
                   WHERE o.supplier_node_id IS NOT NULL
                   GROUP BY o.supplier_node_id, ol.product
               ),
               top AS (
                   SELECT node_id,
                          ARRAY_AGG(product ORDER BY op_count DESC, product) AS products
                   FROM product_ops
                   GROUP BY node_id
               )
               SELECT n.id, n.display_name, n.role, n.latitude, n.longitude,
                      n.zone_label,
                      COALESCE(os.orders_last_week, 0),
                      COALESCE(os.orders_total, 0),
                      COALESCE(top.products[1:%(top_limit)s], ARRAY[]::text[])
               FROM node n
               LEFT JOIN order_stats os ON os.node_id = n.id
               LEFT JOIN top ON top.node_id = n.id
               WHERE n.id IN (
                   SELECT node_id FROM operation
                   UNION
                   SELECT supplier_node_id FROM operation
                   WHERE supplier_node_id IS NOT NULL
               )
               OR n.id = %(me)s
               ORDER BY n.display_name""",
            {"top_limit": TOP_PRODUCTS_LIMIT, "me": user.node_id},
        )
        rows = await cur.fetchall()
    return MapResponse(
        nodes=[
            MapNodeOut(
                id=row[0],
                display_name=row[1],
                role=row[2],
                latitude=row[3],
                longitude=row[4],
                zone_label=row[5],
                orders_last_week=row[6],
                orders_total=row[7],
                top_products=list(row[8]),
            )
            for row in rows
        ]
    )


@router.post("/nodes", status_code=201, response_model=ProducerListItem)
async def create_node(
    body: CreateNodeBody,
    _user: Annotated[AuthUser, Depends(rate_limit_upload)],
) -> ProducerListItem | JSONResponse:
    cuit = body.cuit.strip() if body.cuit else None
    if cuit and not validate_cuit(cuit):
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
                    cuit or None,
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
