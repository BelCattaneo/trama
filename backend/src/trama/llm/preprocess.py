import io

import pypdfium2 as pdfium
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

MAX_PDF_PAGES = 10
_PDF_RENDER_DPI = 150
_JPEG_QUALITY = 85


def pdf_to_images(pdf_bytes: bytes) -> tuple[list[bytes], bool]:
    with pdfium.PdfDocument(pdf_bytes) as pdf:
        total = len(pdf)
        scale = _PDF_RENDER_DPI / 72
        images: list[bytes] = []
        for i in range(min(total, MAX_PDF_PAGES)):
            buf = io.BytesIO()
            pdf[i].render(scale=scale).to_pil().save(buf, format="PNG")
            images.append(buf.getvalue())
        return images, total > MAX_PDF_PAGES


def resize_for_llm(image_bytes: bytes, max_dim: int = 1568) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as img:
        img.thumbnail((max_dim, max_dim))
        rgb = img.convert("RGB")
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=_JPEG_QUALITY)
        return buf.getvalue()
