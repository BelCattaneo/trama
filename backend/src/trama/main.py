from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from trama.config import settings
from trama.db import close_pool, db_ok, open_pool
from trama.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    log = structlog.get_logger()
    await open_pool(settings.database_url, settings.pool_min, settings.pool_max)
    log.info("startup", host=settings.host, port=settings.port)
    yield
    await close_pool()
    log.info("shutdown")


app = FastAPI(title="trama", lifespan=lifespan)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "trama"}


@app.get("/health")
async def health() -> JSONResponse:
    if await db_ok():
        return JSONResponse({"status": "ok", "db": "ok"}, status_code=200)
    return JSONResponse({"status": "degraded", "db": "down"}, status_code=503)
