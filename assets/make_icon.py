"""Generate app icon (ICO + PNG) for LJ Discounts.

Design: rounded square with the accent green (#4ade80) and a bold white "%"
centered. Produces multi-size ICO (16/32/48/64/128/256) and PNG variants.
Run: python assets/make_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ACCENT = (74, 222, 128, 255)
BG_DARK = (8, 9, 13, 255)
SIZES = [16, 32, 48, 64, 128, 256]
OUT = Path(__file__).resolve().parent


def find_bold_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/seguisb.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = max(2, size // 6)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=ACCENT)

    font = find_bold_font(int(size * 0.7))
    text = "%"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1] - size * 0.04
    d.text((x, y), text, fill=BG_DARK, font=font)
    return img


def main() -> None:
    master = draw_icon(256)
    ico_path = OUT / "icon.ico"
    master.save(ico_path, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"wrote {ico_path} ({ico_path.stat().st_size} bytes)")

    for s in (192, 512):
        path = OUT / f"icon-{s}.png"
        draw_icon(s).save(path, format="PNG")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
