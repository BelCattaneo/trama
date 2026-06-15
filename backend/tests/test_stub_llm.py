import json

import pytest

from trama.llm.stub import StubLLMClient, stub_response_var


@pytest.mark.asyncio
async def test_returns_default_empty_payload_when_no_header():
    token = stub_response_var.set(None)
    try:
        result = await StubLLMClient().parse_image(b"image", "prompt")
        assert json.loads(result["text"]) == {"lines": [], "warnings": []}
        assert result["response_id"] is None
    finally:
        stub_response_var.reset(token)


@pytest.mark.asyncio
async def test_uses_canned_payload_from_contextvar():
    payload = {"lines": [{"product": "tomate", "quantity": 5}], "warnings": []}
    token = stub_response_var.set(json.dumps(payload))
    try:
        result = await StubLLMClient().parse_image(b"image", "prompt")
        assert json.loads(result["text"]) == payload
    finally:
        stub_response_var.reset(token)


@pytest.mark.asyncio
async def test_list_payload_pops_one_per_call():
    p1 = {"lines": [{"product": "a", "quantity": 1, "page": 1}], "warnings": []}
    p2 = {"lines": [{"product": "b", "quantity": 2, "page": 2}], "warnings": []}
    token = stub_response_var.set(json.dumps([p1, p2]))
    try:
        client = StubLLMClient()
        first = await client.parse_image(b"image", "prompt")
        second = await client.parse_image(b"image", "prompt")
        assert json.loads(first["text"]) == p1
        assert json.loads(second["text"]) == p2
    finally:
        stub_response_var.reset(token)


@pytest.mark.asyncio
async def test_raise_marker_triggers_error():
    token = stub_response_var.set(json.dumps({"__raise__": True, "message": "boom"}))
    try:
        with pytest.raises(RuntimeError, match="boom"):
            await StubLLMClient().parse_image(b"image", "prompt")
    finally:
        stub_response_var.reset(token)


def test_factory_returns_stub_client_when_provider_is_stub(monkeypatch):
    from trama.llm.factory import get_llm_client

    monkeypatch.setattr("trama.llm.factory.settings.llm_provider", "stub")
    client = get_llm_client()
    assert isinstance(client, StubLLMClient)
