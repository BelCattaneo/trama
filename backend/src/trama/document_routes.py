import hashlib
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from trama import db
from trama.sessions import current_user
from trama.storage import Storage

MAX_BYTES = 10 * 1024 * 1024


class DocumentOut(BaseModel):
    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    content_hash: str
    uploaded_at: datetime


def detect_mime(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"PK\x03\x04") and b"xl/" in data:
        return (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if any("," in line or ";" in line for line in text.splitlines()):
        return "text/csv"
    return None


router = APIRouter(prefix="/api")


@router.post("/documents", status_code=201)
async def upload_document(
    request: Request, file: Annotated[UploadFile, File()]
):
    user = await current_user(request)
    if user is None:
        return JSONResponse({"error": "no autenticado"}, status_code=401)

    contents = await file.read()
    size = len(contents)
    if size == 0:
        return JSONResponse({"error": "archivo vacío"}, status_code=400)
    if size > MAX_BYTES:
        return JSONResponse(
            {"error": "archivo demasiado grande"}, status_code=400
        )

    mime = detect_mime(contents)
    if mime is None:
        return JSONResponse({"error": "formato no soportado"}, status_code=400)

    content_hash = hashlib.sha256(contents).hexdigest()
    storage: Storage = request.app.state.storage
    storage_ref = storage.save(contents, content_hash)

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO document (node_id, original_filename, mime_type,
                                         size_bytes, content_hash, storage_ref)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id, uploaded_at""",
                (
                    user.node_id,
                    file.filename,
                    mime,
                    size,
                    content_hash,
                    storage_ref,
                ),
            )
            doc_id, uploaded_at = await cur.fetchone()

    out = DocumentOut(
        id=doc_id,
        original_filename=file.filename,
        mime_type=mime,
        size_bytes=size,
        content_hash=content_hash,
        uploaded_at=uploaded_at,
    )
    return JSONResponse(out.model_dump(mode="json"), status_code=201)
