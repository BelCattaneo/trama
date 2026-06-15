import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import structlog
from google.genai import errors

from trama.llm.gemini import GeminiClient


@pytest.fixture(autouse=True)
def _structlog_to_stdlib(caplog):
    """Route structlog records through stdlib logging so caplog can capture them."""
    caplog.set_level(logging.DEBUG)
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    yield
    structlog.reset_defaults()


def _make_client(monkeypatch, generate):
    inner = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    )
    monkeypatch.setattr(
        "trama.llm.gemini.genai.Client", MagicMock(return_value=inner)
    )
    return GeminiClient(api_key="test-key-DO-NOT-LOG", model="gemini-2.5-flash")


def _make_response(text="hello world"):
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=12, candidates_token_count=7, total_token_count=19
        ),
        response_id="resp-abc-123",
    )


def _server_error(code=500):
    return errors.ServerError(code=code, response_json={"error": "boom"})


def _client_error(code=400):
    return errors.ClientError(code=code, response_json={"error": "bad input"})


@pytest.mark.asyncio
async def test_success_path_returns_text_and_usage(monkeypatch, caplog):
    generate = AsyncMock(return_value=_make_response("the secret response body"))
    client = _make_client(monkeypatch, generate)

    result = await client.parse_image(b"\x89PNG-bytes", "do not log this prompt")

    assert result["text"] == "the secret response body"
    assert result["usage"] == {
        "prompt_tokens": 12,
        "completion_tokens": 7,
        "total_tokens": 19,
    }
    assert result["response_id"] == "resp-abc-123"
    generate.assert_awaited_once()
    assert any("llm_call_ok" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_5xx_retried_three_times_with_backoff(monkeypatch, caplog):
    generate = AsyncMock(side_effect=_server_error(500))
    client = _make_client(monkeypatch, generate)
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr("trama.llm.gemini.asyncio.sleep", fake_sleep)

    with pytest.raises(errors.ServerError):
        await client.parse_image(b"bytes", "prompt")

    assert generate.await_count == 3
    assert sleeps == [1.0, 2.0]
    retries = [r for r in caplog.records if "llm_call_retry" in r.getMessage()]
    assert len(retries) == 2
    assert any("llm_call_failed" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_4xx_not_retried(monkeypatch, caplog):
    generate = AsyncMock(side_effect=_client_error(400))
    client = _make_client(monkeypatch, generate)
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr("trama.llm.gemini.asyncio.sleep", fake_sleep)

    with pytest.raises(errors.ClientError):
        await client.parse_image(b"bytes", "prompt")

    assert generate.await_count == 1
    assert sleeps == []
    assert not any("llm_call_retry" in r.getMessage() for r in caplog.records)
    assert any("llm_call_failed" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_connection_error_retried_then_raised(monkeypatch, caplog):
    generate = AsyncMock(side_effect=httpx.ConnectError("conn refused"))
    client = _make_client(monkeypatch, generate)
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr("trama.llm.gemini.asyncio.sleep", fake_sleep)

    with pytest.raises(httpx.ConnectError):
        await client.parse_image(b"bytes", "prompt")

    assert generate.await_count == 3
    assert sleeps == [1.0, 2.0]
    retries = [r for r in caplog.records if "llm_call_retry" in r.getMessage()]
    assert len(retries) == 2


@pytest.mark.asyncio
async def test_timeout_raises_without_retry(monkeypatch, caplog):
    async def slow_call(**_kwargs):
        raise TimeoutError("simulated")

    generate = AsyncMock(side_effect=slow_call)
    client = _make_client(monkeypatch, generate)
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr("trama.llm.gemini.asyncio.sleep", fake_sleep)

    with pytest.raises(TimeoutError):
        await client.parse_image(b"bytes", "prompt")

    assert generate.await_count == 1
    assert sleeps == []
    failed = [r for r in caplog.records if "llm_call_failed" in r.getMessage()]
    assert len(failed) == 1


@pytest.mark.asyncio
async def test_logs_never_contain_secrets_prompt_or_response(monkeypatch, caplog):
    secret_prompt = "PROMPT_NEVER_LOG_ME"
    secret_image = b"IMAGE_BYTES_NEVER_LOG_ME"
    secret_response = "RESPONSE_NEVER_LOG_ME"
    api_key = "API_KEY_NEVER_LOG_ME"

    generate = AsyncMock(return_value=_make_response(secret_response))
    inner = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    )
    monkeypatch.setattr(
        "trama.llm.gemini.genai.Client", MagicMock(return_value=inner)
    )
    client = GeminiClient(api_key=api_key, model="gemini-2.5-flash")

    await client.parse_image(secret_image, secret_prompt)

    # Force one retry path to also be exercised in this test.
    generate2 = AsyncMock(
        side_effect=[_server_error(503), _make_response(secret_response)]
    )
    inner.aio.models.generate_content = generate2

    async def fake_sleep(_delay):
        return None

    monkeypatch.setattr("trama.llm.gemini.asyncio.sleep", fake_sleep)
    await client.parse_image(secret_image, secret_prompt)

    for record in caplog.records:
        msg = record.getMessage()
        assert api_key not in msg
        assert secret_prompt not in msg
        assert secret_response not in msg
        assert "IMAGE_BYTES_NEVER_LOG_ME" not in msg
