import io
from collections.abc import Callable
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from trama import db
from trama.parsing._extract import ParseError
from trama.parsing.csv_parser import parse_csv
from trama.parsing.schema import ParsePayload
from trama.parsing.xlsx_parser import parse_xlsx

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_MIME = "text/csv"

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
    if mime_type not in _DETERMINISTIC_PARSERS:
        return None
    result = _run_deterministic(mime_type, contents)
    attempt_id = await _persist(document_id, result)
    return attempt_id, result
