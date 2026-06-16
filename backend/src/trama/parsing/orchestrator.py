import asyncio
import io
from collections.abc import Callable
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict

from trama import db
from trama.llm import get_llm_client
from trama.llm.preprocess import MAX_PDF_PAGES, pdf_to_images, resize_for_llm
from trama.parsing._extract import ParseError
from trama.parsing.csv_parser import parse_csv
from trama.parsing.llm_response import parse_llm_response
from trama.parsing.schema import ParseLine, ParsePayload
from trama.parsing.xlsx_parser import parse_xlsx
from trama.prompts import load_prompt

logger = structlog.get_logger(__name__)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_MIME = "text/csv"
PDF_MIME = "application/pdf"

_LLM_MIMES = frozenset(
    {"image/jpeg", "image/png", "image/heic", "image/heif", PDF_MIME}
)
_LLM_PROMPT_VERSION = "v1"

CONFIDENCE_EMPTY_LINES = 0.3
CONFIDENCE_NOISY = 0.5
CONFIDENCE_HAS_WARNINGS = 0.8
CONFIDENCE_CLEAN = 1.0
NOISY_WARNING_RATIO = 0.5

_DETERMINISTIC_PARSERS: dict[str, Callable[[object], ParsePayload]] = {
    XLSX_MIME: parse_xlsx,
    CSV_MIME: parse_csv,
}


class ParseResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: str
    confidence: float
    payload: ParsePayload | None
    error_message: str | None
    prompt_version: str | None = None


def _compute_confidence(payload: ParsePayload) -> float:
    lines = len(payload.lines)
    warnings = len(payload.warnings)
    if lines == 0:
        return CONFIDENCE_EMPTY_LINES
    if warnings / (lines + warnings) >= NOISY_WARNING_RATIO:
        return CONFIDENCE_NOISY
    if warnings > 0:
        return CONFIDENCE_HAS_WARNINGS
    return CONFIDENCE_CLEAN


def _run_deterministic(mime_type: str, contents: bytes) -> ParseResult:
    parser = _DETERMINISTIC_PARSERS[mime_type]
    try:
        payload = parser(io.BytesIO(contents))
    except ParseError as exc:
        return ParseResult(
            strategy="deterministic",
            confidence=0.0,
            payload=None,
            error_message=str(exc),
        )
    return ParseResult(
        strategy="deterministic",
        confidence=_compute_confidence(payload),
        payload=payload,
        error_message=None,
    )


def _prepare_pages(mime_type: str, contents: bytes) -> tuple[list[bytes], bool]:
    if mime_type != PDF_MIME:
        return [resize_for_llm(contents)], False
    raw_pages, truncated = pdf_to_images(contents)
    return [resize_for_llm(p) for p in raw_pages], truncated


def _tag_lines_with_page(payload: ParsePayload, page: int) -> list[ParseLine]:
    return [line.model_copy(update={"page": page}) for line in payload.lines]


async def _run_llm(mime_type: str, contents: bytes, llm_client) -> ParseResult:
    try:
        pages, pdf_truncated = await asyncio.to_thread(
            _prepare_pages, mime_type, contents
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "llm_preprocess_failed",
            mime_type=mime_type,
            error_type=type(exc).__name__,
        )
        return ParseResult(
            strategy="llm",
            confidence=0.0,
            payload=None,
            error_message=f"preprocess failed: {type(exc).__name__}",
            prompt_version=_LLM_PROMPT_VERSION,
        )
    prompt = load_prompt(_LLM_PROMPT_VERSION)

    all_lines: list[ParseLine] = []
    all_warnings: list[str] = []
    page_errors: list[str] = []

    for idx, page_bytes in enumerate(pages):
        page_num = idx + 1
        try:
            result = await llm_client.parse_image(page_bytes, prompt)
            payload = parse_llm_response(result["text"])
        except Exception as exc:  # noqa: BLE001
            error_type = type(exc).__name__
            logger.exception(
                "llm_page_failed", page=page_num, error_type=error_type
            )
            page_errors.append(f"[p{page_num}] página falló: {error_type}")
            all_warnings.append(f"[p{page_num}] página falló: {error_type}")
            continue

        all_lines.extend(_tag_lines_with_page(payload, page_num))
        all_warnings.extend(f"[p{page_num}] {w}" for w in payload.warnings)

    if pdf_truncated:
        all_warnings.append(
            f"PDF tiene más de {MAX_PDF_PAGES} páginas, "
            f"solo se procesaron las primeras {MAX_PDF_PAGES}"
        )

    if not all_lines and len(page_errors) == len(pages):
        return ParseResult(
            strategy="llm",
            confidence=0.0,
            payload=None,
            error_message="; ".join(page_errors),
            prompt_version=_LLM_PROMPT_VERSION,
        )

    payload = ParsePayload(lines=all_lines, warnings=all_warnings)
    return ParseResult(
        strategy="llm",
        confidence=_compute_confidence(payload),
        payload=payload,
        error_message=None,
        prompt_version=_LLM_PROMPT_VERSION,
    )


async def _persist(document_id: UUID, result: ParseResult) -> UUID:
    payload_json = result.payload.model_dump_json() if result.payload else None
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO parse_attempt (document_id, strategy, confidence,
                                              payload, prompt_version, error_message)
                   VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                   RETURNING id""",
                (
                    document_id,
                    result.strategy,
                    result.confidence,
                    payload_json,
                    result.prompt_version,
                    result.error_message,
                ),
            )
            (attempt_id,) = await cur.fetchone()
    return attempt_id


async def run_parse(
    document_id: UUID, mime_type: str, contents: bytes
) -> tuple[UUID, ParseResult] | None:
    """Dispatch by mime, persist the parse_attempt. None for unparseable mimes."""
    if mime_type in _DETERMINISTIC_PARSERS:
        result = _run_deterministic(mime_type, contents)
    elif mime_type in _LLM_MIMES:
        result = await _run_llm(mime_type, contents, get_llm_client())
    else:
        return None
    attempt_id = await _persist(document_id, result)
    return attempt_id, result
