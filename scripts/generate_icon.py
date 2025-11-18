#!/usr/bin/env python3
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


HOME = Path(__file__).resolve().parents[1]
ICON_PATH = HOME / "src" / "pdfnotebook" / "static" / "app_icon.png"


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Return a properly framed PNG chunk with length and CRC."""
    length = struct.pack(">I", len(data))
    chunk = length + chunk_type + data
    crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    return chunk + crc


def build_image(width: int, height: int) -> bytes:
    """Generate RGBA image data for the custom icon."""
    def lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    background_top = (18, 32, 72)
    background_bottom = (24, 122, 189)
    page_base = (246, 248, 255)
    accent_line = (82, 91, 152)

    rows = bytearray()
    for y in range(height):
        rows.append(0)  # no filter
        t = y / (height - 1)
        bg_r = int(lerp(background_top[0], background_bottom[0], t))
        bg_g = int(lerp(background_top[1], background_bottom[1], t))
        bg_b = int(lerp(background_top[2], background_bottom[2], t))
        for x in range(width):
            r, g, b = bg_r, bg_g, bg_b
            page_margin = 8
            corner_radius = 3
            is_page = (
                page_margin <= x < width - page_margin
                and page_margin <= y < height - page_margin
            )
            if is_page:
                progress = (x - page_margin) / (width - 2 * page_margin - 1)
                corner = (
                    abs((x - (width - page_margin)) - corner_radius)
                    if x > width - page_margin - corner_radius
                    else abs(x - page_margin - corner_radius)
                )
                lighten = 1 - min(1.0, (y - page_margin) / (height - 2 * page_margin - 1))
                r = int(lerp(page_base[0], page_base[0] - 12, 1 - progress))
                g = int(lerp(page_base[1], page_base[1] - 8, 1 - progress))
                b = int(lerp(page_base[2], page_base[2] - 6, 1 - progress))
                if y - page_margin < 4:
                    r = min(255, r + 10)
                    g = min(255, g + 10)
                    b = min(255, b + 10)
                if (
                    x - page_margin < corner_radius
                    or (width - page_margin - 1 - x) < corner_radius
                    or y - page_margin < corner_radius
                ):
                    distance = math.hypot(
                        min(x - page_margin, width - page_margin - 1 - x),
                        min(y - page_margin, height - page_margin - 1 - y),
                    )
                    if distance > corner_radius:
                        is_page = False
            if is_page:
                # add accent lines for writing
                if (x - page_margin) % 6 in (1, 2, 3) and (y - page_margin) % 10 in (
                    2,
                    3,
                ):
                    r, g, b = accent_line
            rows.extend((r, g, b, 255))
    return bytes(rows)


def write_icon() -> None:
    """Create PNG file with handcrafted visuals."""
    width = 64
    height = 64
    ICON_PATH.parent.mkdir(parents=True, exist_ok=True)
    image_data = build_image(width, height)
    with ICON_PATH.open("wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n")
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
        handle.write(png_chunk(b"IHDR", ihdr))
        handle.write(png_chunk(b"IDAT", zlib.compress(image_data, level=9)))
        handle.write(png_chunk(b"IEND", b""))


if __name__ == "__main__":
    write_icon()
