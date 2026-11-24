#!/usr/bin/env python3
"""Draw the world news of Monday 23 November 2026 as one 1024x1024 image.

Pure Python standard library: the picture is drawn into an RGB buffer with
a small embedded 5x7 bitmap font and written out as a PNG with zlib.
No network, no files read, no randomness: the same bytes every run.

Run:  python3 main.py        (writes /output/entry.png, or $MAKEFUN_OUTPUT_DIR)
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font -----
# 5x7 bitmap font, uppercase only. Each glyph is 7 rows of 5 bits.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
}


def text_width(text, scale):
    """Pixel width of text at the given scale (6 px advance per glyph)."""
    return len(text) * 6 * scale


# -------------------------------------------------------------- canvas -----
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def fill_rect(self, x, y, w, h, color):
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.w), min(y + h, self.h)
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, color, t=1):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for a in range(t):
                for b in range(t):
                    self.set(x0 + a, y0 + b, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color, t=1, fill=False):
        import math
        if fill:
            for yy in range(-r, r + 1):
                half = int(math.sqrt(max(r * r - yy * yy, 0)))
                self.fill_rect(cx - half, cy + yy, half * 2 + 1, 1, color)
            return
        steps = max(8, int(2 * 3.14159 * r))
        for i in range(steps):
            a = 2 * 3.14159 * i / steps
            x = int(cx + r * math.cos(a) + 0.5)
            y = int(cy + r * math.sin(a) + 0.5)
            for a2 in range(t):
                for b2 in range(t):
                    self.set(x + a2, y + b2, color)

    def ellipse(self, cx, cy, rx, ry, color, t=1):
        import math
        steps = max(16, int(2 * 3.14159 * max(rx, ry)))
        for i in range(steps):
            a = 2 * 3.14159 * i / steps
            x = int(cx + rx * math.cos(a) + 0.5)
            y = int(cy + ry * math.sin(a) + 0.5)
            for a2 in range(t):
                for b2 in range(t):
                    self.set(x + a2, y + b2, color)

    def triangle(self, p1, p2, p3, color):
        # Filled triangle via scanline fill.
        pts = sorted([p1, p2, p3], key=lambda p: p[1])
        (x1, y1), (x2, y2), (x3, y3) = pts
        def interp(xa, ya, xb, yb, y):
            if yb == ya:
                return xa
            return xa + (xb - xa) * (y - ya) / (yb - ya)
        for y in range(y1, y3 + 1):
            if y < y2:
                xa = interp(x1, y1, x2, y2, y)
                xb = interp(x1, y1, x3, y3, y)
            else:
                xa = interp(x2, y2, x3, y3, y)
                xb = interp(x1, y1, x3, y3, y)
            lo, hi = sorted((int(xa), int(xb)))
            self.fill_rect(lo, y, hi - lo + 1, 1, color)

    def text(self, x, y, s, color, scale=2):
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, color)
            cx += 6 * scale

    def text_center(self, cx, y, s, color, scale=2):
        self.text(cx - text_width(s, scale) // 2, y, s, color, scale)


# ----------------------------------------------------------------- png -----
def write_png(path, canvas):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        raw += canvas.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ------------------------------------------------------------ pictograms ----
# Each draws inside a ~150px tall area centred on (cx, cy).

def pic_globe(c, cx, cy, accent):
    # COP31: a globe with a red slash across it — no deal.
    c.circle(cx, cy, 52, accent, t=5)
    c.ellipse(cx, cy, 52, 20, accent, t=3)
    c.ellipse(cx, cy, 20, 52, accent, t=3)
    c.line(cx - 52, cy, cx + 52, cy, accent, t=3)
    c.line(cx - 40, cy - 40, cx + 40, cy + 40, (200, 40, 30), t=7)


def pic_ship(c, cx, cy, accent):
    # Merkury: a warship listing in the waves, blast above it.
    c.triangle((cx - 62, cy - 8), (cx + 58, cy - 8), (cx + 34, cy + 26), accent)
    c.fill_rect(cx - 62, cy - 8, 120, 10, accent)
    c.fill_rect(cx - 8, cy - 52, 8, 44, accent)
    c.fill_rect(cx - 26, cy - 34, 44, 8, accent)
    c.circle(cx - 40, cy + 4, 5, (255, 255, 255), t=1, fill=True)
    # blast star
    bx, by = cx + 44, cy - 62
    for dx, dy in ((0, -16), (0, 16), (-16, 0), (16, 0),
                   (-11, -11), (11, -11), (-11, 11), (11, 11)):
        c.line(bx, by, bx + dx, by + dy, (230, 120, 20), t=5)
    # waves
    for wy in (cy + 42, cy + 56):
        for k in range(-3, 4):
            c.line(cx + k * 20 - 8, wy, cx + k * 20 + 8, wy - 6,
                   (60, 120, 180), t=3)
            c.line(cx + k * 20 + 8, wy - 6, cx + k * 20 + 24, wy,
                   (60, 120, 180), t=3)


def pic_building(c, cx, cy, accent):
    # Kyiv: a block of flats, its top corner shattered, blast above.
    c.fill_rect(cx - 46, cy - 44, 92, 96, accent)
    c.fill_rect(cx - 46, cy - 44, 92, 10, (60, 60, 70))
    for r in range(4):
        for col in range(3):
            c.fill_rect(cx - 34 + col * 30, cy - 24 + r * 22, 16, 12,
                        (255, 220, 120))
    # shattered corner: jagged notch top-right
    c.triangle((cx + 10, cy - 44), (cx + 46, cy - 44), (cx + 46, cy - 12),
               (244, 241, 232))
    c.triangle((cx + 22, cy - 44), (cx + 46, cy - 44), (cx + 34, cy - 26),
               (244, 241, 232))
    bx, by = cx + 30, cy - 66
    for dx, dy in ((0, -14), (0, 14), (-14, 0), (14, 0),
                   (-10, -10), (10, -10), (-10, 10), (10, 10)):
        c.line(bx, by, bx + dx, by + dy, (230, 120, 20), t=5)


def pic_factory(c, cx, cy, accent):
    # Indonesia: a factory with a chimney and flames.
    c.fill_rect(cx - 58, cy - 6, 116, 58, accent)
    c.fill_rect(cx - 58, cy - 22, 116, 16, accent)
    for k in range(4):
        c.triangle((cx - 58 + k * 29, cy - 22), (cx - 44 + k * 29, cy - 38),
                   (cx - 29 + k * 29, cy - 22), accent)
    c.fill_rect(cx + 44, cy - 66, 16, 118, accent)
    c.fill_rect(cx + 40, cy - 72, 24, 8, accent)
    # flames
    for fx, fh, col in ((cx - 44, 44, (230, 120, 20)),
                        (cx - 20, 58, (240, 170, 30)),
                        (cx + 4, 46, (230, 120, 20)),
                        (cx + 24, 34, (240, 170, 30))):
        c.triangle((fx - 12, cy - 22), (fx, cy - 22 - fh),
                   (fx + 12, cy - 22), col)


def pic_mercury(c, cx, cy, accent):
    # BepiColombo: cratered Mercury, orbit ring, small craft.
    c.ellipse(cx, cy, 78, 26, (120, 120, 130), t=3)
    c.circle(cx, cy, 44, accent, t=5)
    c.circle(cx - 14, cy - 10, 7, accent, t=1, fill=True)
    c.circle(cx + 12, cy + 8, 9, accent, t=1, fill=True)
    c.circle(cx + 16, cy - 18, 5, accent, t=1, fill=True)
    c.circle(cx - 4, cy + 18, 4, accent, t=1, fill=True)
    # spacecraft on the ring, upper right
    sx, sy = cx + 62, cy - 24
    c.fill_rect(sx - 8, sy - 6, 16, 12, (40, 40, 50))
    c.fill_rect(sx - 30, sy - 3, 20, 6, (60, 120, 180))
    c.fill_rect(sx + 10, sy - 3, 20, 6, (60, 120, 180))


def pic_zeta(c, cx, cy, accent):
    # Riemann: axes, a wavy zeta-like curve, and a green check.
    c.line(cx - 62, cy + 30, cx + 62, cy + 30, (90, 90, 100), t=3)
    c.line(cx - 62, cy - 56, cx - 62, cy + 30, (90, 90, 100), t=3)
    import math
    prev = None
    for i in range(121):
        x = cx - 58 + i
        y = int(cy - 6 - 26 * math.sin(i / 9.0) * math.exp(-i / 220.0))
        if prev is not None:
            c.line(prev[0], prev[1], x, y, accent, t=3)
        prev = (x, y)
    # green check in a circle, lower right
    gx, gy = cx + 44, cy + 34
    c.circle(gx, gy, 20, (30, 160, 90), t=4)
    c.line(gx - 10, gy, gx - 2, gy + 9, (30, 160, 90), t=5)
    c.line(gx - 2, gy + 9, gx + 12, gy - 9, (30, 160, 90), t=5)


# -------------------------------------------------------------- stories -----
# tag, accent colour, headline lines, sub lines, pictogram
STORIES = [
    ("CLIMATE", (30, 130, 80),
     ["COP31:", "NO DEAL"],
     ["CLIMATE TALKS IN ANTALYA", "END WITH NO AGREEMENT", "FIRST COLLAPSE SINCE 2009"],
     pic_globe),
    ("WAR AT SEA", (170, 40, 40),
     ["WARSHIP SUNK", "OFF LIBYA"],
     ["UKRAINE DRONES SINK THE", "RUSSIAN CORVETTE MERKURY", "AT BENGHAZI, LIBYA"],
     pic_ship),
    ("UKRAINE", (170, 40, 40),
     ["15 KILLED", "NEAR KYIV"],
     ["OVERNIGHT STRIKES HIT", "HOMES AROUND KYIV;", "BOY, 7, PULLED ALIVE"],
     pic_building),
    ("DISASTER", (200, 110, 20),
     ["24 DEAD IN", "FACTORY FIRE"],
     ["CANDY FACTORY BLAZE IN", "BANTEN, INDONESIA;", "30 STILL MISSING"],
     pic_factory),
    ("SPACE", (90, 60, 160),
     ["BEPICOLOMBO", "REACHES", "MERCURY"],
     ["ESA CRAFT SAFE IN ORBIT", "AFTER 8-YEAR TRIP;", "GLITCH TRACED TO SOFTWARE"],
     pic_mercury),
    ("SCIENCE", (20, 120, 130),
     ["AI MATH PROOF", "CHECKS", "ADVANCE"],
     ["RIEMANN PROOF: LEAN", "VERIFICATION ADVANCES;", "EXPERTS STILL DIVIDED"],
     pic_zeta),
]

NAVY = (11, 31, 58)
PAPER = (244, 241, 232)
INK = (25, 25, 30)
MUTED = (90, 90, 100)


# ----------------------------------------------------------------- page -----
def draw_page():
    c = Canvas(W, H, PAPER)

    # Header
    c.fill_rect(0, 0, W, 148, NAVY)
    c.fill_rect(0, 148, W, 4, (200, 160, 40))
    c.text_center(W // 2, 26, "MONDAY 23 NOVEMBER 2026", (255, 255, 255), 5)
    c.text_center(W // 2, 92, "THE WORLD IN ONE DAY", (200, 160, 40), 3)
    # small globe mark at the left of the header
    c.circle(72, 74, 30, (200, 160, 40), t=3)
    c.ellipse(72, 74, 30, 12, (200, 160, 40), t=2)
    c.ellipse(72, 74, 12, 30, (200, 160, 40), t=2)
    c.circle(952, 74, 30, (200, 160, 40), t=3)
    c.ellipse(952, 74, 30, 12, (200, 160, 40), t=2)
    c.ellipse(952, 74, 12, 30, (200, 160, 40), t=2)

    # Panels: 3 columns x 2 rows
    pw, ph, gap, mx = 322, 388, 12, 17
    top0 = 164
    for i, (tag, accent, head, sub, pic) in enumerate(STORIES):
        x = mx + (i % 3) * (pw + gap)
        y = top0 + (i // 3) * (ph + gap)
        c.fill_rect(x, y, pw, ph, (255, 255, 255))
        c.rect(x, y, pw, ph, (200, 196, 180), t=2)
        # tag band
        c.fill_rect(x + 2, y + 2, pw - 4, 30, accent)
        c.text(x + 14, y + 8, tag, (255, 255, 255), 2)
        # pictogram
        pic(c, x + pw // 2, y + 116, accent)
        # headline (up to 3 lines)
        hy = y + 200
        for line in head:
            c.text_center(x + pw // 2, hy, line, INK, 4)
            hy += 30
        # divider
        c.fill_rect(x + 24, hy + 2, pw - 48, 2, accent)
        # sub lines
        sy = hy + 12
        for line in sub:
            c.text_center(x + pw // 2, sy, line, MUTED, 2)
            sy += 20

    # Footer
    fy = 964
    c.fill_rect(0, fy - 8, W, 2, (200, 196, 180))
    c.text_center(W // 2, fy + 8,
                  "AS REPORTED ON 23 NOV 2026 - REUTERS - AP - ESA - WRI",
                  MUTED, 2)
    c.text_center(W // 2, fy + 32, "MAKE.FUN - NEWS-IMAGE-20261123",
                  MUTED, 2)
    return c


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    canvas = draw_page()
    write_png(os.path.join(outdir, "entry.png"), canvas)


if __name__ == "__main__":
    main()
