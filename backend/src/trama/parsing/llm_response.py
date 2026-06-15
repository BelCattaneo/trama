import json
from typing import Literal

from pydantic import ValidationError

from trama.parsing.schema import ParsePayload


class LLMResponseError(Exception):
    def __init__(
        self,
        kind: Literal["invalid_json", "schema_mismatch"],
        message: str | None = None,
    ):
        self.kind = kind
        super().__init__(message or kind)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    if text.startswith("```json"):
        text = text[len("```json") :]
    else:
        text = text[len("```") :]
    if text.endswith("```"):
        text = text[: -len("```")]
    return text.strip()


def parse_llm_response(text: str) -> ParsePayload:
    cleaned = _strip_fences(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMResponseError(kind="invalid_json", message=str(exc)) from exc
    try:
        return ParsePayload.model_validate(parsed)
    except ValidationError as exc:
        raise LLMResponseError(kind="schema_mismatch", message=str(exc)) from exc
