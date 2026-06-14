from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from trama.config import settings
from trama.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    log = structlog.get_logger()
    log.info("startup", host=settings.host, port=settings.port)
    yield
    log.info("shutdown")


app = FastAPI(title="trama", lifespan=lifespan)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "trama"}
