import math
from collections import Counter

import structlog

from trama.parsing.schema import (
    ConfirmCorrection,
    ConfirmLine,
    CorrectionField,
    ParseLine,
    ParsePayload,
)

logger = structlog.get_logger(__name__)

_QUANTITY_REL_TOL = 1e-9
_QUANTITY_ABS_TOL = 1e-6


def _line_fields_differ(original: ParseLine, final: ConfirmLine) -> list[CorrectionField]:
    """Per-field comparison; raw_text and page are intentionally excluded."""
    changed: list[CorrectionField] = []
    if original.product != final.product:
        changed.append("product")
    if not math.isclose(
        original.quantity,
        final.quantity,
        rel_tol=_QUANTITY_REL_TOL,
        abs_tol=_QUANTITY_ABS_TOL,
    ):
        changed.append("quantity")
    if original.unit != final.unit:
        changed.append("unit")
    return changed


def diff_payloads(
    original: ParsePayload,
    final_lines: list[ConfirmLine],
    client_corrections: list[ConfirmCorrection],
) -> None:
    """Compare server-detected diffs to client-reported corrections and log discrepancies.

    The client remains authoritative; this is an audit hook for catching frontend bugs.
    Original line identity is the 0-based index in ``original.lines``.
    """
    # Server-side diff bag. line_added entries use line_no=None because added lines
    # have no original counterpart; counts let us distinguish multiple added lines.
    server_diffs: Counter[tuple[int | None, CorrectionField]] = Counter()

    original_by_line: dict[int, ParseLine] = dict(enumerate(original.lines))
    final_by_line: dict[int, ConfirmLine] = {}
    for final in final_lines:
        if final.line_no is None:
            server_diffs[(None, "line_added")] += 1
        else:
            final_by_line[final.line_no] = final

    for line_no, original_line in original_by_line.items():
        final_line = final_by_line.get(line_no)
        if final_line is None:
            server_diffs[(line_no, "line_removed")] += 1
            continue
        for field in _line_fields_differ(original_line, final_line):
            server_diffs[(line_no, field)] += 1

    client_diffs: Counter[tuple[int | None, CorrectionField]] = Counter(
        (c.line_no, c.field) for c in client_corrections
    )

    for key, server_count in server_diffs.items():
        line_no, field = key
        extra = server_count - client_diffs.get(key, 0)
        for _ in range(extra):
            logger.warning(
                "correction_diff_discrepancy",
                direction="client_only",
                line_no=line_no,
                field=field,
            )

    for key, client_count in client_diffs.items():
        line_no, field = key
        extra = client_count - server_diffs.get(key, 0)
        for _ in range(extra):
            logger.warning(
                "correction_diff_discrepancy",
                direction="server_only",
                line_no=line_no,
                field=field,
            )
