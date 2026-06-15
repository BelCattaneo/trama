import io

import pypdfium2 as pdfium
from PIL import Image
from pillow_heif import register_heif_opener

# Register HEIC as a Pillow plugin so Image.open accepts it.
register_heif_opener()

MAX_PDF_PAGES = 10
_PDF_RENDER_DPI = 150
_JPEG_QUALITY = 85


def pdf_to_images(pdf_bytes: bytes) -> list[bytes]:
    """Render each PDF page at 150 DPI to PNG bytes, capped at MAX_PDF_PAGES."""
    pdf = pdfium.PdfDocument(pdf_bytes)
    page_count = min(len(pdf), MAX_PDF_PAGES)
    scale = _PDF_RENDER_DPI / 72
    images: list[bytes] = []
    for i in range(page_count):
        page = pdf[i]
        pil_image = page.render(scale=scale).to_pil()
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        images.append(buf.getvalue())
    return images


def resize_for_llm(image_bytes: bytes, max_dim: int = 1568) -> bytes:
    """Scale longest side to <= max_dim, preserve aspect ratio, re-encode as JPEG q85."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        img.thumbnail((max_dim, max_dim))
        rgb = img.convert("RGB")
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=_JPEG_QUALITY)
        return buf.getvalue()
