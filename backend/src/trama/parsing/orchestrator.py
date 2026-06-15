from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from trama import db
from trama.parsing._extract import ParseError
from trama.parsing.csv_parser import parse_csv
from trama.parsing.schema import ParsePayload
from trama.parsing.xlsx_parser import parse_xlsx

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_MIME = "text/csv"

_DETERMINISTIC_PARSERS: dict[str, Callable[[object], ParsePayload]] = {
    XLSX_MIME: parse_xlsx,
    CSV_MIME: parse_csv,
}


@dataclass(frozen=True)
class ParseResult:
    strategy: str
    confidence: float
    payload: ParsePayload | None
    error_message: str | None
    prompt_version: str | None = None


def _compute_confidence(payload: ParsePayload) -> float:
    lines = len(payload.lines)
    warnings = len(payload.warnings)
    if lines == 0:
        return 0.3
    total = lines + warnings
    if total > 0 and warnings / total >= 0.5:
        return 0.5
    if warnings > 0:
        return 0.8
    return 1.0


def _run_deterministic(mime_type: str, contents: bytes) -> ParseResult:
    import io

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
    """Dispatch to the right parser by mime type, persist a parse_attempt.
    Returns (attempt_id, ParseResult) when a parser ran; None for mime types
    without a parser yet (pdf, jpeg, png).
    """
    if mime_type not in _DETERMINISTIC_PARSERS:
        return None
    result = _run_deterministic(mime_type, contents)
    attempt_id = await _persist(document_id, result)
    return attempt_id, result
