from typing import BinaryIO

from openpyxl import load_workbook

from trama.parsing._extract import ParseError, extract_payload
from trama.parsing.schema import ParsePayload


def parse_xlsx(stream: BinaryIO) -> ParsePayload:
    """Parse an .xlsx file stream into a ParsePayload.
    Raises ParseError if no recognizable header row is found.
    """
    workbook = load_workbook(stream, read_only=True, data_only=True)
    sheet = workbook.active
    if sheet is None:
        raise ParseError("no se encontraron columnas reconocidas")

    rows = [list(r) for r in sheet.iter_rows(values_only=True)]
    return extract_payload(rows)
