import pytest

from trama.cuit import validate_cuit

VALID_CUITS = [
    "20-12345678-6",
    "30-50001091-2",
    "33-69345023-9",
    "20-11111111-2",
    "27-12345678-0",
    "23-12345678-5",
]

INVALID_CUITS = [
    "20-12345678-9",      # wrong checksum
    "invalid",            # non-digit
    "",                   # empty
    "20-1234567-6",       # too short
    "20-123456789-6",     # too long
    "20-1234567A-6",      # non-digit inside
]


@pytest.mark.parametrize("cuit", VALID_CUITS)
def test_valid_cuits(cuit):
    assert validate_cuit(cuit) is True


@pytest.mark.parametrize("cuit", INVALID_CUITS)
def test_invalid_cuits(cuit):
    assert validate_cuit(cuit) is False


def test_accepts_dashless_format():
    assert validate_cuit("20123456786") is True
