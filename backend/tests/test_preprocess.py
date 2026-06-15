import io

import pytest
from PIL import Image

from trama.llm.preprocess import MAX_PDF_PAGES, pdf_to_images, resize_for_llm

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _make_image_bytes(size: tuple[int, int], fmt: str, color: str = "red") -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _make_pdf_bytes(page_count: int) -> bytes:
    pages = [Image.new("RGB", (200, 300), "white") for _ in range(page_count)]
    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
    return buf.getvalue()


@pytest.fixture(scope="session")
def large_jpeg_bytes() -> bytes:
    return _make_image_bytes((2400, 1600), "JPEG")


@pytest.fixture(scope="session")
def png_bytes() -> bytes:
    return _make_image_bytes((1800, 1200), "PNG", color="blue")


@pytest.fixture(scope="session")
def heic_bytes() -> bytes:
    img = Image.new("RGB", (1800, 1200), "green")
    buf = io.BytesIO()
    img.save(buf, format="HEIF")
    return buf.getvalue()


@pytest.fixture(scope="session")
def small_jpeg_bytes() -> bytes:
    return _make_image_bytes((400, 300), "JPEG", color="purple")


@pytest.fixture(scope="session")
def pdf_3_pages() -> bytes:
    return _make_pdf_bytes(3)


@pytest.fixture(scope="session")
def pdf_15_pages() -> bytes:
    return _make_pdf_bytes(15)


def _open_jpeg(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


def test_large_jpeg_resized_to_max_dim(large_jpeg_bytes):
    out = resize_for_llm(large_jpeg_bytes)
    with _open_jpeg(out) as img:
        assert img.format == "JPEG"
        assert max(img.size) <= 1568
        # Aspect ratio preserved: original 2400x1600 → ratio 3:2 → 1568x ~1045
        assert img.size == (1568, 1045)


def test_png_input_outputs_jpeg(png_bytes):
    out = resize_for_llm(png_bytes)
    with _open_jpeg(out) as img:
        assert img.format == "JPEG"
        assert max(img.size) <= 1568


def test_heic_input_outputs_jpeg(heic_bytes):
    out = resize_for_llm(heic_bytes)
    with _open_jpeg(out) as img:
        assert img.format == "JPEG"
        assert max(img.size) <= 1568


def test_small_image_still_reencoded_as_jpeg(small_jpeg_bytes):
    out = resize_for_llm(small_jpeg_bytes)
    assert out != small_jpeg_bytes
    with _open_jpeg(out) as img:
        assert img.format == "JPEG"
        assert img.size == (400, 300)


def test_pdf_three_pages_returns_three_pngs(pdf_3_pages):
    pages = pdf_to_images(pdf_3_pages)
    assert len(pages) == 3
    for page in pages:
        assert page.startswith(PNG_MAGIC)


def test_pdf_fifteen_pages_capped_at_ten(pdf_15_pages):
    pages = pdf_to_images(pdf_15_pages)
    assert len(pages) == MAX_PDF_PAGES == 10
    for page in pages:
        assert page.startswith(PNG_MAGIC)
