import csv
from typing import BinaryIO

from trama.parsing._extract import ParseError, extract_payload
from trama.parsing.schema import ParsePayload


def _detect_delimiter(first_line: str) -> str:
    comma_count = first_line.count(",")
    semicolon_count = first_line.count(";")
    if semicolon_count > comma_count:
        return ";"
    return ","


def parse_csv(stream: BinaryIO) -> ParsePayload:
    """Parse a UTF-8 CSV stream into a ParsePayload."""
    data = stream.read()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError(
            "el archivo no está en UTF-8. Guardalo como CSV UTF-8 desde Excel "
            "(Archivo → Guardar como → CSV UTF-8)"
        ) from exc

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ParseError("no se encontraron columnas reconocidas")

    delimiter = _detect_delimiter(lines[0])
    try:
        rows = list(csv.reader(lines, delimiter=delimiter))
    except csv.Error as exc:
        raise ParseError("csv inválido") from exc
    return extract_payload(rows)
