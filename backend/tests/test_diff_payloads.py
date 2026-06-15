import logging

import pytest
import structlog

from trama.parsing.diff import diff_payloads
from trama.parsing.schema import (
    ConfirmCorrection,
    ConfirmLine,
    ParseLine,
    ParsePayload,
)


@pytest.fixture(autouse=True)
def _structlog_to_stdlib(caplog):
    """Route structlog records through stdlib logging so caplog can capture them."""
    caplog.set_level(logging.DEBUG)
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    yield
    structlog.reset_defaults()


def _discrepancy_records(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if "correction_diff_discrepancy" in r.getMessage()]


def _make_line(product="papa", quantity=10.0, unit="kg") -> ParseLine:
    return ParseLine(product=product, quantity=quantity, unit=unit, raw_text=None, page=1)


def _make_confirm(
    line_no: int | None,
    product="papa",
    quantity=10.0,
    unit="kg",
) -> ConfirmLine:
    return ConfirmLine(
        line_no=line_no,
        product=product,
        quantity=quantity,
        unit=unit,
        raw_text=None,
        page=1,
    )


def test_client_and_server_agree_on_single_field_edit(caplog):
    original = ParsePayload(lines=[_make_line(product="papa", quantity=10.0)])
    final = [_make_confirm(line_no=0, product="papa andina", quantity=10.0)]
    corrections = [
        ConfirmCorrection(
            line_no=0,
            field="product",
            original_value="papa",
            corrected_value="papa andina",
        )
    ]

    diff_payloads(original, final, corrections)

    assert _discrepancy_records(caplog) == []


def test_client_adds_line_and_reports_line_added(caplog):
    original = ParsePayload(lines=[_make_line()])
    final = [
        _make_confirm(line_no=0),
        _make_confirm(line_no=None, product="cebolla", quantity=5.0),
    ]
    corrections = [
        ConfirmCorrection(
            line_no=None,
            field="line_added",
            original_value=None,
            corrected_value="cebolla 5 kg",
        )
    ]

    diff_payloads(original, final, corrections)

    assert _discrepancy_records(caplog) == []


def test_client_edits_quantity_but_forgets_to_report(caplog):
    original = ParsePayload(lines=[_make_line(product="papa", quantity=10.0)])
    final = [_make_confirm(line_no=0, product="papa", quantity=12.0)]

    diff_payloads(original, final, [])

    records = _discrepancy_records(caplog)
    assert len(records) == 1
    msg = records[0].getMessage()
    assert '"direction": "client_only"' in msg
    assert '"field": "quantity"' in msg
    assert '"line_no": 0' in msg


def test_client_reports_correction_server_sees_unchanged(caplog):
    original = ParsePayload(lines=[_make_line(product="papa", quantity=10.0)])
    final = [_make_confirm(line_no=0, product="papa", quantity=10.0)]
    corrections = [
        ConfirmCorrection(
            line_no=0,
            field="product",
            original_value="papa",
            corrected_value="papa",
        )
    ]

    diff_payloads(original, final, corrections)

    records = _discrepancy_records(caplog)
    assert len(records) == 1
    msg = records[0].getMessage()
    assert '"direction": "server_only"' in msg
    assert '"field": "product"' in msg
    assert '"line_no": 0' in msg


def test_payload_unchanged_no_corrections(caplog):
    original = ParsePayload(
        lines=[_make_line(product="papa"), _make_line(product="cebolla")]
    )
    final = [
        _make_confirm(line_no=0, product="papa"),
        _make_confirm(line_no=1, product="cebolla"),
    ]

    diff_payloads(original, final, [])

    assert _discrepancy_records(caplog) == []


def test_float_comparison_treats_close_values_as_equal(caplog):
    original = ParsePayload(lines=[_make_line(quantity=5.0)])
    final = [_make_confirm(line_no=0, quantity=5.000000001)]

    diff_payloads(original, final, [])

    assert _discrepancy_records(caplog) == []


def test_removed_line_reported_by_client(caplog):
    original = ParsePayload(
        lines=[
            _make_line(product="papa"),
            _make_line(product="cebolla"),
            _make_line(product="zanahoria"),
        ]
    )
    final = [
        _make_confirm(line_no=0, product="papa"),
        _make_confirm(line_no=2, product="zanahoria"),
    ]
    corrections = [
        ConfirmCorrection(
            line_no=1,
            field="line_removed",
            original_value="cebolla",
            corrected_value=None,
        )
    ]

    diff_payloads(original, final, corrections)

    assert _discrepancy_records(caplog) == []


def test_removed_line_not_reported_by_client(caplog):
    original = ParsePayload(
        lines=[
            _make_line(product="papa"),
            _make_line(product="cebolla"),
            _make_line(product="zanahoria"),
        ]
    )
    final = [
        _make_confirm(line_no=0, product="papa"),
        _make_confirm(line_no=2, product="zanahoria"),
    ]

    diff_payloads(original, final, [])

    records = _discrepancy_records(caplog)
    assert len(records) == 1
    msg = records[0].getMessage()
    assert '"direction": "client_only"' in msg
    assert '"field": "line_removed"' in msg
    assert '"line_no": 1' in msg


def test_logs_never_contain_original_or_corrected_values(caplog):
    secret_original = "SECRET_ORIGINAL_VALUE_NEVER_LOG"
    secret_corrected = "SECRET_CORRECTED_VALUE_NEVER_LOG"
    original = ParsePayload(lines=[_make_line(product=secret_original, quantity=10.0)])
    final = [_make_confirm(line_no=0, product=secret_corrected, quantity=10.0)]
    corrections = [
        ConfirmCorrection(
            line_no=0,
            field="quantity",
            original_value=secret_original,
            corrected_value=secret_corrected,
        )
    ]

    diff_payloads(original, final, corrections)

    for record in caplog.records:
        msg = record.getMessage()
        assert secret_original not in msg
        assert secret_corrected not in msg
