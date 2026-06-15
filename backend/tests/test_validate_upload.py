import pytest
from fastapi import HTTPException

from trama.document_routes import MAX_BYTES, _validate_upload


def test_returns_mime_for_valid_pdf():
    assert _validate_upload(b"%PDF-1.4\n%body\n") == "application/pdf"


def test_returns_mime_for_valid_csv():
    assert _validate_upload(b"name,qty\napple,3\n") == "text/csv"


def test_rejects_empty():
    with pytest.raises(HTTPException) as exc:
        _validate_upload(b"")
    assert exc.value.status_code == 400
    assert exc.value.detail == "archivo vacío"


def test_rejects_oversize():
    payload = b"%PDF-" + b"x" * (MAX_BYTES + 1 - len(b"%PDF-"))
    with pytest.raises(HTTPException) as exc:
        _validate_upload(payload)
    assert exc.value.status_code == 400
    assert exc.value.detail == "archivo demasiado grande"


def test_accepts_exactly_max_bytes():
    payload = b"%PDF-" + b"x" * (MAX_BYTES - len(b"%PDF-"))
    assert len(payload) == MAX_BYTES
    assert _validate_upload(payload) == "application/pdf"


def test_accepts_heic():
    assert (
        _validate_upload(b"\x00\x00\x00\x20ftypheic" + b"\x00" * 8) == "image/heic"
    )


def test_rejects_unknown_mime():
    with pytest.raises(HTTPException) as exc:
        _validate_upload(b"\x00" * 32)
    assert exc.value.status_code == 400
    assert exc.value.detail == "formato no soportado"


def test_rejects_utf8_text_without_delimiter():
    with pytest.raises(HTTPException) as exc:
        _validate_upload(b"this is just prose no comma no semicolon\nstill prose\n")
    assert exc.value.status_code == 400
    assert exc.value.detail == "formato no soportado"
