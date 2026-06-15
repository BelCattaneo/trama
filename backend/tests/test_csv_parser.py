import io
from pathlib import Path

import pytest

from trama.parsing._extract import ParseError
from trama.parsing.csv_parser import parse_csv

FIXTURES = Path(__file__).parent / "fixtures" / "parsing"


def _read(name: str) -> io.BytesIO:
    return io.BytesIO((FIXTURES / name).read_bytes())


def test_standard_five_rows_no_warnings():
    payload = parse_csv(_read("standard.csv"))
    products = [line.product for line in payload.lines]
    assert products == [
        "Zanahoria",
        "Tomate perita",
        "Lechuga",
        "Manzana",
        "Pera",
    ]
    assert payload.warnings == []


def test_semicolon_delimiter_detected():
    payload = parse_csv(_read("semicolon.csv"))
    assert len(payload.lines) == 4
    assert payload.warnings == []
    products = [line.product for line in payload.lines]
    assert "Tomate cherry" in products
    cherry = next(line for line in payload.lines if line.product == "Tomate cherry")
    assert cherry.quantity == 1.5  # comma decimal with ; delimiter


def test_semicolon_with_comma_decimal_quarter():
    payload = parse_csv(_read("semicolon.csv"))
    limon = next(line for line in payload.lines if line.product == "Limón")
    assert limon.quantity == 3.25


def test_latin1_raises_parse_error_with_actionable_message():
    with pytest.raises(ParseError) as exc:
        parse_csv(_read("latin1.csv"))
    msg = str(exc.value)
    assert "UTF-8" in msg
    assert "Excel" in msg


def test_malformed_skips_invalid_with_warnings():
    payload = parse_csv(_read("malformed.csv"))
    products = [line.product for line in payload.lines]
    assert products == ["Zanahoria", "Manzana"]
    joined = " ".join(payload.warnings)
    assert "sin cantidad" in joined
    assert "cantidad inválida" in joined
    assert "sin producto" in joined


def test_malformed_comma_decimal_with_semicolon_delim():
    payload = parse_csv(_read("malformed.csv"))
    manzana = next(line for line in payload.lines if line.product == "Manzana")
    assert manzana.quantity == 1.5


def test_bom_tolerated():
    payload = parse_csv(_read("bom.csv"))
    assert len(payload.lines) == 1
    assert payload.lines[0].product == "Zanahoria"
    assert payload.lines[0].quantity == 3.0


def test_no_recognizable_headers_raises():
    with pytest.raises(ParseError) as exc:
        parse_csv(_read("no_headers.csv"))
    assert "no se encontraron columnas reconocidas" in str(exc.value)


def test_empty_file_raises():
    with pytest.raises(ParseError):
        parse_csv(io.BytesIO(b""))


def test_only_headers_returns_empty_payload():
    payload = parse_csv(io.BytesIO(b"Producto,Cantidad\n"))
    assert payload.lines == []
    assert payload.warnings == []


def test_delimiter_heuristic_comma_wins_when_both_present():
    data = b"Producto,Cantidad,Unidad\nZanahoria,3,kg\n"
    payload = parse_csv(io.BytesIO(data))
    assert payload.lines[0].quantity == 3.0


def test_delimiter_default_comma_when_neither_present():
    # Single column with only product → not enough; should raise
    data = b"Producto\nZanahoria\n"
    with pytest.raises(ParseError):
        parse_csv(io.BytesIO(data))
