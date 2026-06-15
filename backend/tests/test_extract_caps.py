"""Caps and canonical-only raw_text in extract_payload (security/PII)."""

from trama.parsing._extract import (
    _MAX_LINES,
    _MAX_WARNINGS,
    _RAW_TEXT_MAX_CHARS,
    extract_payload,
)


def _headers_row() -> list[str]:
    return ["Producto", "Cantidad", "Unidad"]


def test_raw_text_only_includes_canonical_cells():
    """A non-canonical cell (e.g. an address) must NOT leak into raw_text."""
    rows = [
        ["Producto", "Cantidad", "Notas privadas", "Unidad"],
        ["Zanahoria", 3, "tel 11-1234-5678", "kg"],
    ]
    payload = extract_payload(rows)
    assert len(payload.lines) == 1
    raw_text = payload.lines[0].raw_text
    assert raw_text is not None
    assert "Zanahoria" in raw_text
    assert "kg" in raw_text
    assert "tel" not in raw_text
    assert "1234" not in raw_text


def test_raw_text_truncated_at_max_chars():
    big = "x" * (_RAW_TEXT_MAX_CHARS + 100)
    rows = [_headers_row(), [big, 1, "kg"]]
    payload = extract_payload(rows)
    raw_text = payload.lines[0].raw_text
    assert raw_text is not None
    assert len(raw_text) <= _RAW_TEXT_MAX_CHARS


def test_lines_capped():
    rows = [_headers_row()]
    for i in range(_MAX_LINES + 50):
        rows.append([f"p{i}", 1, "kg"])
    payload = extract_payload(rows)
    assert len(payload.lines) == _MAX_LINES
    assert any("excede el máximo" in w for w in payload.warnings)


def test_warnings_capped():
    rows = [_headers_row()]
    # Each row missing product → 1 warning per row
    for _ in range(_MAX_WARNINGS + 50):
        rows.append(["", 1, "kg"])
    payload = extract_payload(rows)
    # No lines extracted, only warnings
    assert len(payload.lines) == 0
    assert len(payload.warnings) <= _MAX_WARNINGS
