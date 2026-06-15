import pytest

from trama.parsing.llm_response import LLMResponseError, parse_llm_response
from trama.parsing.schema import ParsePayload


def test_clean_json_returns_valid_payload():
    text = (
        '{"lines": [{"product": "tomate", "quantity": 5.0, '
        '"unit": "kg", "raw_text": "tomate 5kg"}], "warnings": []}'
    )
    payload = parse_llm_response(text)
    assert isinstance(payload, ParsePayload)
    assert len(payload.lines) == 1
    assert payload.lines[0].product == "tomate"
    assert payload.lines[0].quantity == 5.0
    assert payload.lines[0].unit == "kg"
    assert payload.lines[0].raw_text == "tomate 5kg"
    assert payload.warnings == []


def test_markdown_json_fenced_payload_parses():
    text = (
        "```json\n"
        '{"lines": [{"product": "tomate", "quantity": 5.0, '
        '"unit": "kg", "raw_text": "tomate 5kg"}], "warnings": []}\n'
        "```"
    )
    payload = parse_llm_response(text)
    assert isinstance(payload, ParsePayload)
    assert payload.lines[0].product == "tomate"


def test_plain_fenced_payload_parses():
    text = (
        "```\n"
        '{"lines": [{"product": "tomate", "quantity": 5.0, '
        '"unit": "kg", "raw_text": "tomate 5kg"}], "warnings": []}\n'
        "```"
    )
    payload = parse_llm_response(text)
    assert isinstance(payload, ParsePayload)
    assert payload.lines[0].quantity == 5.0


def test_malformed_json_raises_invalid_json():
    with pytest.raises(LLMResponseError) as exc_info:
        parse_llm_response("not json {")
    assert exc_info.value.kind == "invalid_json"


def test_missing_required_field_raises_schema_mismatch():
    text = '{"lines": [{"product": "tomate"}], "warnings": []}'
    with pytest.raises(LLMResponseError) as exc_info:
        parse_llm_response(text)
    assert exc_info.value.kind == "schema_mismatch"


def test_string_in_float_field_raises_schema_mismatch():
    text = (
        '{"lines": [{"product": "tomate", "quantity": "unreadable", '
        '"unit": null, "raw_text": null}], "warnings": []}'
    )
    with pytest.raises(LLMResponseError) as exc_info:
        parse_llm_response(text)
    assert exc_info.value.kind == "schema_mismatch"


def test_empty_lines_with_warnings_is_valid():
    text = '{"lines": [], "warnings": ["imagen ilegible"]}'
    payload = parse_llm_response(text)
    assert isinstance(payload, ParsePayload)
    assert payload.lines == []
    assert payload.warnings == ["imagen ilegible"]
