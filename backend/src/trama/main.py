from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from trama.auth_routes import router as auth_router
from trama.config import settings
from trama.db import close_pool, db_ok, open_pool
from trama.log import configure_logging
from trama.storage import LocalStorage
from trama.user_routes import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    log = structlog.get_logger()
    await open_pool(settings.database_url, settings.pool_min, settings.pool_max)
    app.state.storage = LocalStorage(settings.storage_path)
    log.info("startup", host=settings.host, port=settings.port)
    yield
    await close_pool()
    log.info("shutdown")


app = FastAPI(title="trama", lifespan=lifespan)

allowed_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "trama"}


@app.get("/health")
async def health() -> JSONResponse:
    if await db_ok():
        return JSONResponse({"status": "ok", "db": "ok"}, status_code=200)
    return JSONResponse({"status": "degraded", "db": "down"}, status_code=503)
