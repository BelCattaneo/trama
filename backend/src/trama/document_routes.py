import hashlib
from datetime import datetime
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from trama import db
from trama.parsing.orchestrator import run_parse
from trama.parsing.schema import ParsePayload
from trama.sessions import AuthUser, require_user
from trama.storage import Storage

MAX_BYTES = 10 * 1024 * 1024


class DocumentOut(BaseModel):
    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    content_hash: str
    uploaded_at: datetime


class ParseAttemptOut(BaseModel):
    id: UUID
    strategy: str
    confidence: float
    payload: ParsePayload | None
    error_message: str | None


class ReviewParseAttemptOut(BaseModel):
    id: UUID
    strategy: str
    confidence: float
    payload: ParsePayload | None
    prompt_version: str | None
    error_message: str | None
    is_winner: bool
    created_at: datetime


class UploadResponse(BaseModel):
    document: DocumentOut
    parse_attempt: ParseAttemptOut | None


class DocumentsListResponse(BaseModel):
    documents: list[DocumentOut]


class ReparseResponse(BaseModel):
    parse_attempt: ParseAttemptOut


class ReviewResponse(BaseModel):
    document: DocumentOut
    parse_attempt: ReviewParseAttemptOut | None


_HEIC_BRANDS = (b"heic", b"heix", b"hevc", b"mif1")


def detect_mime(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in _HEIC_BRANDS:
        return "image/heic"
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


def _validate_upload(contents: bytes) -> str:
    size = len(contents)
    if size == 0:
        raise HTTPException(status_code=400, detail="archivo vacío")
    if size > MAX_BYTES:
        raise HTTPException(status_code=400, detail="archivo demasiado grande")
    mime = detect_mime(contents)
    if mime is None:
        raise HTTPException(status_code=400, detail="formato no soportado")
    return mime


router = APIRouter(prefix="/api")


@router.post("/documents", status_code=201)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File()],
    user: Annotated[AuthUser, Depends(require_user)],
):
    contents = await file.read()
    mime = _validate_upload(contents)
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
                    len(contents),
                    content_hash,
                    storage_ref,
                ),
            )
            doc_id, uploaded_at = await cur.fetchone()

    document = DocumentOut(
        id=doc_id,
        original_filename=file.filename,
        mime_type=mime,
        size_bytes=len(contents),
        content_hash=content_hash,
        uploaded_at=uploaded_at,
    )

    parse_attempt = None
    parsed = await run_parse(doc_id, mime, contents)
    if parsed is not None:
        attempt_id, result = parsed
        parse_attempt = ParseAttemptOut(
            id=attempt_id,
            strategy=result.strategy,
            confidence=result.confidence,
            payload=result.payload,
            error_message=result.error_message,
        )

    out = UploadResponse(document=document, parse_attempt=parse_attempt)
    return JSONResponse(out.model_dump(mode="json"), status_code=201)


@router.get("/documents", response_model=DocumentsListResponse)
async def list_documents(
    user: Annotated[AuthUser, Depends(require_user)],
) -> DocumentsListResponse:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, original_filename, mime_type, size_bytes,
                          content_hash, uploaded_at
                   FROM document
                   WHERE node_id = %s
                   ORDER BY uploaded_at DESC""",
                (user.node_id,),
            )
            rows = await cur.fetchall()
    return DocumentsListResponse(
        documents=[
            DocumentOut(
                id=r[0],
                original_filename=r[1],
                mime_type=r[2],
                size_bytes=r[3],
                content_hash=r[4],
                uploaded_at=r[5],
            )
            for r in rows
        ]
    )


def _content_disposition(filename: str) -> str:
    try:
        filename.encode("ascii")
        safe = filename.replace("\\", "\\\\").replace('"', '\\"')
        return f'inline; filename="{safe}"'
    except UnicodeEncodeError:
        return f"inline; filename*=UTF-8''{quote(filename, safe='')}"


@router.get("/documents/{document_id}/file")
async def get_document_file(
    request: Request,
    document_id: UUID,
    user: Annotated[AuthUser, Depends(require_user)],
) -> Response:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT original_filename, mime_type, storage_ref
                   FROM document
                   WHERE id = %s AND node_id = %s""",
                (document_id, user.node_id),
            )
            row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="documento no encontrado")
    original_filename, mime_type, storage_ref = row

    storage: Storage = request.app.state.storage
    try:
        contents = storage.get(storage_ref)
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=500, detail="no se pudo leer el archivo"
        ) from err

    return Response(
        content=contents,
        media_type=mime_type,
        headers={
            "Content-Disposition": _content_disposition(original_filename),
            "Cache-Control": "private, max-age=300",
        },
    )


@router.post("/documents/{document_id}/reparse")
async def reparse_document(
    request: Request,
    document_id: UUID,
    user: Annotated[AuthUser, Depends(require_user)],
) -> ReparseResponse:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT mime_type, storage_ref
                   FROM document
                   WHERE id = %s AND node_id = %s""",
                (document_id, user.node_id),
            )
            row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="documento no encontrado")
    mime_type, storage_ref = row

    storage: Storage = request.app.state.storage
    contents = storage.get(storage_ref)

    parsed = await run_parse(document_id, mime_type, contents)
    if parsed is None:
        raise HTTPException(
            status_code=400, detail="este formato todavía no tiene parser"
        )
    attempt_id, result = parsed
    parse_attempt = ParseAttemptOut(
        id=attempt_id,
        strategy=result.strategy,
        confidence=result.confidence,
        payload=result.payload,
        error_message=result.error_message,
    )
    return ReparseResponse(parse_attempt=parse_attempt)


@router.get("/documents/{document_id}/review", response_model=ReviewResponse)
async def review_document(
    document_id: UUID,
    user: Annotated[AuthUser, Depends(require_user)],
) -> ReviewResponse:
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, original_filename, mime_type, size_bytes,
                          content_hash, uploaded_at
                   FROM document
                   WHERE id = %s AND node_id = %s""",
                (document_id, user.node_id),
            )
            doc_row = await cur.fetchone()
            if doc_row is None:
                raise HTTPException(
                    status_code=404, detail="documento no encontrado"
                )
            await cur.execute(
                """SELECT id, strategy, confidence, payload, prompt_version,
                          error_message, is_winner, created_at
                   FROM parse_attempt
                   WHERE document_id = %s
                   ORDER BY created_at DESC
                   LIMIT 1""",
                (document_id,),
            )
            attempt_row = await cur.fetchone()

    document = DocumentOut(
        id=doc_row[0],
        original_filename=doc_row[1],
        mime_type=doc_row[2],
        size_bytes=doc_row[3],
        content_hash=doc_row[4],
        uploaded_at=doc_row[5],
    )
    parse_attempt = None
    if attempt_row is not None:
        parse_attempt = ReviewParseAttemptOut(
            id=attempt_row[0],
            strategy=attempt_row[1],
            confidence=attempt_row[2],
            payload=attempt_row[3],
            prompt_version=attempt_row[4],
            error_message=attempt_row[5],
            is_winner=attempt_row[6],
            created_at=attempt_row[7],
        )
    return ReviewResponse(document=document, parse_attempt=parse_attempt)
