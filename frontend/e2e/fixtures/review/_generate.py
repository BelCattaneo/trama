"""Regenerate the e2e review fixtures.

Run from the backend uv env so we get Pillow, openpyxl, pillow_heif:
    uv run --directory backend python ../frontend/e2e/fixtures/review/_generate.py

Outputs go next to this script. Synthetic data only — no real producer info.
"""

from pathlib import Path

from openpyxl import Workbook
from PIL import Image, ImageDraw
from pillow_heif import register_heif_opener

register_heif_opener()

OUT_DIR = Path(__file__).parent


def write_clean_table() -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["Producto", "Cantidad", "Unidad"])
    ws.append(["tomate", 5, "kg"])
    ws.append(["cebolla", 3, "atados"])
    ws.append(["zanahoria", 2, "kg"])
    wb.save(OUT_DIR / "clean_table.xlsx")


def _text_image(text: str, size=(400, 300)) -> Image.Image:
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), text, fill="black")
    return img


def write_clean_photo() -> None:
    img = _text_image("tomate 5kg\ncebolla 3 atados")
    img.save(OUT_DIR / "clean_photo.jpg", format="JPEG", quality=80)


def write_iphone_photo() -> None:
    img = _text_image("tomate 5kg\ncebolla 3 atados")
    img.save(OUT_DIR / "iphone_photo.heic", format="HEIF")


def write_pdf(path: Path, pages: int) -> None:
    images = [_text_image(f"page {i + 1}\ntomate 5kg") for i in range(pages)]
    first, rest = images[0], images[1:]
    first.save(path, format="PDF", save_all=True, append_images=rest)


def main() -> None:
    write_clean_table()
    write_clean_photo()
    write_iphone_photo()
    write_pdf(OUT_DIR / "multi_page.pdf", pages=3)
    write_pdf(OUT_DIR / "huge.pdf", pages=15)
    print(f"wrote fixtures to {OUT_DIR}")


if __name__ == "__main__":
    main()
