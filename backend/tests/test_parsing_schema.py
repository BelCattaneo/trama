import pytest
from pydantic import ValidationError

from trama.parsing.schema import ParseLine, ParsePayload


def test_empty_payload_valid():
    payload = ParsePayload()
    assert payload.lines == []
    assert payload.warnings == []


def test_minimal_line():
    line = ParseLine(product="zanahoria", quantity=3.5)
    assert line.product == "zanahoria"
    assert line.quantity == 3.5
    assert line.unit is None
    assert line.raw_text is None


def test_full_line():
    line = ParseLine(
        product="tomate perita",
        quantity=2.0,
        unit="kg",
        raw_text="tomate perita | 2 | kg",
    )
    assert line.unit == "kg"
    assert line.raw_text == "tomate perita | 2 | kg"


def test_negative_quantity_allowed():
    line = ParseLine(product="x", quantity=-1.0)
    assert line.quantity == -1.0


def test_empty_product_allowed():
    line = ParseLine(product="", quantity=1.0)
    assert line.product == ""


def test_payload_with_lines_and_warnings():
    payload = ParsePayload(
        lines=[
            ParseLine(product="a", quantity=1.0),
            ParseLine(product="b", quantity=2.0),
        ],
        warnings=["fila 3 sin cantidad"],
    )
    assert len(payload.lines) == 2
    assert payload.warnings == ["fila 3 sin cantidad"]


def test_roundtrip_json():
    original = ParsePayload(
        lines=[ParseLine(product="zanahoria", quantity=3.5, unit="kg")],
        warnings=["fila 4 saltada"],
    )
    s = original.model_dump_json()
    restored = ParsePayload.model_validate_json(s)
    assert restored == original


def test_line_frozen():
    line = ParseLine(product="x", quantity=1.0)
    with pytest.raises(ValidationError):
        line.product = "y"


def test_payload_frozen():
    payload = ParsePayload()
    with pytest.raises(ValidationError):
        payload.lines = [ParseLine(product="a", quantity=1.0)]
