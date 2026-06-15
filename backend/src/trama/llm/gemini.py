import asyncio
import time

import httpx
import structlog
from google import genai
from google.genai import errors, types

logger = structlog.get_logger(__name__)

_RETRYABLE_HTTPX = (
    httpx.ConnectError,
    httpx.ReadError,
    httpx.RemoteProtocolError,
    httpx.TimeoutException,
)
_RETRYABLE = (errors.ServerError, *_RETRYABLE_HTTPX)

_BACKOFFS_S = (1.0, 2.0, 4.0)
_TIMEOUT_S = 30.0
_MAX_ATTEMPTS = 3


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = genai.Client(api_key=api_key)

    async def parse_image(self, image_bytes: bytes, prompt: str) -> dict:
        part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        started = time.monotonic()

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self._model,
                        contents=[part, prompt],
                    ),
                    timeout=_TIMEOUT_S,
                )
            except _RETRYABLE as exc:
                if attempt < _MAX_ATTEMPTS:
                    backoff = _BACKOFFS_S[attempt - 1]
                    logger.warning(
                        "llm_call_retry",
                        provider="gemini",
                        attempt=attempt,
                        error_type=type(exc).__name__,
                        status_code=getattr(exc, "code", None),
                        backoff_ms=int(backoff * 1000),
                    )
                    await asyncio.sleep(backoff)
                    continue
                self._log_failed(exc, attempt, started)
                raise
            except (errors.ClientError, TimeoutError) as exc:
                self._log_failed(exc, attempt, started)
                raise

            return self._build_result(response, started)

    def _log_failed(self, exc: Exception, attempts: int, started: float) -> None:
        latency_ms = int((time.monotonic() - started) * 1000)
        logger.warning(
            "llm_call_failed",
            provider="gemini",
            error_type=type(exc).__name__,
            status_code=getattr(exc, "code", None),
            attempts=attempts,
            latency_ms=latency_ms,
        )

    def _build_result(self, response, started: float) -> dict:
        latency_ms = int((time.monotonic() - started) * 1000)
        usage = response.usage_metadata
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage, "total_token_count", 0) or 0
        response_id = getattr(response, "response_id", None)
        logger.info(
            "llm_call_ok",
            provider="gemini",
            model=self._model,
            response_id=response_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )
        return {
            "text": response.text,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "response_id": response_id,
        }
