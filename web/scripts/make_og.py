"""Generate the 1200x630 social-share card with no external deps (stdlib only).

Same primitives as make_icons.py — evergreen-black field, amber marquee bar,
coral stage block — plus "PNW STAGE" set in a 5x7 pixel font.
Run: python scripts/make_og.py
"""
import struct
import zlib
from pathlib import Path

W, H = 1200, 630
BG = (11, 15, 13, 255)      # ink-900
AMBER = (245, 181, 68, 255) # marquee bulbs bar
CORAL = (255, 90, 60, 255)  # stage block

# 5x7 glyphs, one string row per scanline, "1" = lit pixel.
FONT = {
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}
TEXT = "PNW STAGE"
SCALE = 18                      # glyph pixel -> 18 image px (letters 90x126)
ADVANCE = 6 * SCALE             # 5 columns + 1 column of tracking
TEXT_W = len(TEXT) * ADVANCE - SCALE
TEXT_X = (W - TEXT_W) // 2
TEXT_Y = 240

BAR_TOP, BAR_BOT = 120, 158     # amber marquee bar
STAGE_TOP, STAGE_BOT = 430, 470 # coral stage block under the wordmark


def lit(x: int, y: int) -> bool:
    if not (TEXT_Y <= y < TEXT_Y + 7 * SCALE):
        return False
    tx = x - TEXT_X
    if tx < 0 or tx >= TEXT_W:
        return False
    idx, gx = divmod(tx, ADVANCE)
    col, gy = gx // SCALE, (y - TEXT_Y) // SCALE
    return col < 5 and FONT[TEXT[idx]][gy][col] == "1"


def render() -> bytes:
    px = bytearray()
    for y in range(H):
        px.append(0)  # PNG filter type 0 for each scanline
        for x in range(W):
            if BAR_TOP <= y <= BAR_BOT and 168 <= x <= W - 168:
                c = AMBER
            elif lit(x, y):
                c = CORAL
            elif STAGE_TOP <= y <= STAGE_BOT and TEXT_X <= x <= TEXT_X + TEXT_W:
                c = AMBER
            else:
                c = BG
            px.extend(c)
    return bytes(px)


def chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(
        ">I", zlib.crc32(tag + data) & 0xFFFFFFFF
    )


def png() -> bytes:
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)  # 8-bit RGBA
    idat = zlib.compress(render(), 9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "public"
    out.mkdir(exist_ok=True)
    (out / "og.png").write_bytes(png())
    print("wrote public/og.png")
