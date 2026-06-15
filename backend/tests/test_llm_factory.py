from unittest.mock import MagicMock

import pytest

from trama.llm.factory import get_llm_client
from trama.llm.gemini import GeminiClient


def test_returns_gemini_client_when_key_set(monkeypatch):
    monkeypatch.setattr("trama.llm.factory.settings.llm_provider", "gemini")
    monkeypatch.setattr("trama.llm.factory.settings.llm_model", "gemini-2.5-flash")
    monkeypatch.setattr(
        "trama.llm.factory.settings.google_api_key", "test-key-DO-NOT-LOG"
    )
    monkeypatch.setattr(
        "trama.llm.gemini.genai.Client", MagicMock(return_value=MagicMock())
    )

    client = get_llm_client()
    assert isinstance(client, GeminiClient)


def test_raises_when_gemini_key_missing(monkeypatch):
    monkeypatch.setattr("trama.llm.factory.settings.llm_provider", "gemini")
    monkeypatch.setattr("trama.llm.factory.settings.google_api_key", None)

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY required"):
        get_llm_client()


def test_raises_when_gemini_key_empty_string(monkeypatch):
    monkeypatch.setattr("trama.llm.factory.settings.llm_provider", "gemini")
    monkeypatch.setattr("trama.llm.factory.settings.google_api_key", "")

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY required"):
        get_llm_client()


def test_raises_on_unsupported_provider(monkeypatch):
    monkeypatch.setattr("trama.llm.factory.settings.llm_provider", "anthropic")

    with pytest.raises(RuntimeError, match="unsupported LLM_PROVIDER=anthropic"):
        get_llm_client()
