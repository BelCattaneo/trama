"""Test-only LLM client — must not be enabled in production.

Returns canned responses read from a contextvar populated by an HTTP middleware
that inspects the X-LLM-Stub-Response header. The header is honored only when
LLM_PROVIDER=stub; the factory enforces that. The middleware is wired in main.py
and refuses to read the header on other providers as defense in depth.
"""

import json
from contextvars import ContextVar

stub_response_var: ContextVar[str | None] = ContextVar(
    "stub_response_var", default=None
)

_DEFAULT_PAYLOAD = {
    "text": '{"lines": [], "warnings": []}',
    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    "response_id": None,
}


class StubLLMClient:
    async def parse_image(self, image_bytes: bytes, prompt: str) -> dict:
        raw = stub_response_var.get()
        if raw is None:
            return dict(_DEFAULT_PAYLOAD)
        decoded = json.loads(raw)
        if isinstance(decoded, dict) and decoded.get("__raise__"):
            raise RuntimeError(decoded.get("message") or "stub LLM forced failure")
        if isinstance(decoded, list):
            # First entry is consumed; the rest stays for subsequent pages.
            if not decoded:
                return dict(_DEFAULT_PAYLOAD)
            current = decoded[0]
            stub_response_var.set(json.dumps(decoded[1:]))
        else:
            current = decoded
        if isinstance(current, dict) and current.get("__raise__"):
            raise RuntimeError(current.get("message") or "stub LLM forced failure")
        return {
            "text": json.dumps(current) if not isinstance(current, str) else current,
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "response_id": None,
        }
