from trama.parsing.columns import REQUIRED_FIELDS, canonicalize_columns
from trama.parsing.schema import ParseLine, ParsePayload

_HEADER_SCAN_ROWS = 5
_MAX_LINES = 10_000
_MAX_WARNINGS = 10_000
_RAW_TEXT_MAX_CHARS = 2_000


class ParseError(Exception):
    """Raised when the parser cannot extract any usable lines."""


def _parse_quantity(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _row_to_strings(row) -> list[str]:
    return ["" if c is None else str(c) for c in row]


def _row_is_empty(row) -> bool:
    return all(c is None or str(c).strip() == "" for c in row)


def _find_header(rows: list[list]) -> tuple[int, dict[str, str]]:
    for idx, row in enumerate(rows[:_HEADER_SCAN_ROWS]):
        if _row_is_empty(row):
            continue
        mapping = canonicalize_columns(_row_to_strings(row))
        if REQUIRED_FIELDS.issubset(set(mapping.values())):
            return idx, mapping
    raise ParseError("no se encontraron columnas reconocidas")


def _build_canonical_raw_text(
    canonical_by_col_idx: dict[int, str], row: list
) -> str | None:
    parts: list[str] = []
    for col_idx in sorted(canonical_by_col_idx):
        if col_idx >= len(row):
            continue
        cell = row[col_idx]
        text = "" if cell is None else str(cell).strip()
        if text:
            parts.append(text)
    if not parts:
        return None
    joined = " | ".join(parts)
    if len(joined) > _RAW_TEXT_MAX_CHARS:
        joined = joined[:_RAW_TEXT_MAX_CHARS]
    return joined


def extract_payload(rows: list[list]) -> ParsePayload:
    """Convert tabular rows into a validated ParsePayload."""
    if not rows:
        raise ParseError("no se encontraron columnas reconocidas")

    header_idx, mapping = _find_header(rows)
    header_strings = _row_to_strings(rows[header_idx])
    canonical_by_col_idx: dict[int, str] = {}
    for col_idx, header in enumerate(header_strings):
        if header in mapping:
            canonical_by_col_idx[col_idx] = mapping[header]

    lines: list[ParseLine] = []
    warnings: list[str] = []
    truncated = False

    for row_offset, row in enumerate(rows[header_idx + 1 :], start=1):
        if len(lines) >= _MAX_LINES:
            truncated = True
            break
        row_num = header_idx + 1 + row_offset
        if _row_is_empty(row):
            continue

        fields: dict[str, object] = {}
        for col_idx, canonical in canonical_by_col_idx.items():
            if col_idx < len(row):
                fields[canonical] = row[col_idx]

        product = fields.get("product")
        product_str = "" if product is None else str(product).strip()
        if not product_str:
            if len(warnings) < _MAX_WARNINGS:
                warnings.append(f"fila {row_num} sin producto, saltada")
            continue

        raw_qty = fields.get("quantity")
        if raw_qty is None or (isinstance(raw_qty, str) and not raw_qty.strip()):
            if len(warnings) < _MAX_WARNINGS:
                warnings.append(f"fila {row_num} sin cantidad, saltada")
            continue
        quantity = _parse_quantity(raw_qty)
        if quantity is None:
            if len(warnings) < _MAX_WARNINGS:
                warnings.append(
                    f"fila {row_num} con cantidad inválida: '{raw_qty}', saltada"
                )
            continue

        unit_value = fields.get("unit")
        unit_text = str(unit_value).strip() if unit_value is not None else ""
        unit = unit_text or None

        raw_text = _build_canonical_raw_text(canonical_by_col_idx, row)

        lines.append(
            ParseLine(
                product=product_str,
                quantity=quantity,
                unit=unit,
                raw_text=raw_text,
            )
        )

    if truncated:
        warnings.append(
            f"el documento excede el máximo de {_MAX_LINES} filas y se cortó"
        )

    return ParsePayload(lines=lines, warnings=warnings)
