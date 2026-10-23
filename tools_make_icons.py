# -*- coding: utf-8 -*-
"""Generates the PWA icon set for the apartment-charge app (no external deps beyond Pillow)."""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "icons")
os.makedirs(OUT, exist_ok=True)

TOP = (37, 78, 216)     # #254ed8-ish
BOT = (29, 78, 216)     # #1d4ed8
BRAND = (29, 78, 216)
WHITE = (255, 255, 255, 255)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(size, c1, c2):
    img = Image.new("RGB", (1, size), c1)
    px = img.load()
    for y in range(size):
        px[0, y] = lerp(c1, c2, y / max(1, size - 1))
    return img.resize((size, size), Image.BILINEAR)


def rounded_mask(size, radius_ratio):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    r = int(size * radius_ratio)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    return m


def draw_building(d, size, scale=1.0, cy=None):
    """White apartment block with a window grid and a door, centred."""
    s = size
    if cy is None:
        cy = s / 2.0
    # building footprint
    bw = 0.46 * s * scale
    bh = 0.50 * s * scale
    bx = (s - bw) / 2.0
    by = cy - bh / 2.0 + 0.035 * s * scale

    # roof slab
    roof_h = 0.045 * s * scale
    d.rounded_rectangle(
        [bx - 0.045 * s * scale, by - roof_h, bx + bw + 0.045 * s * scale, by + 0.012 * s * scale],
        radius=int(0.018 * s * scale), fill=WHITE)

    # body
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=int(0.030 * s * scale), fill=WHITE)

    # window grid 3 x 3
    cols, rows = 3, 3
    pad_x = 0.085 * bw
    pad_y = 0.080 * bh
    gap_x = 0.065 * bw
    gap_y = 0.075 * bh
    ww = (bw - 2 * pad_x - (cols - 1) * gap_x) / cols
    wh = (bh - 2 * pad_y - (rows - 1) * gap_y) / rows
    for r in range(rows):
        for c in range(cols):
            x0 = bx + pad_x + c * (ww + gap_x)
            y0 = by + pad_y + r * (wh + gap_y)
            d.rounded_rectangle([x0, y0, x0 + ww, y0 + wh],
                                radius=int(min(ww, wh) * 0.22), fill=BRAND)

    # door
    dw = 0.20 * bw
    dh = 0.20 * bh
    dx = bx + (bw - dw) / 2.0
    dy = by + bh - dh
    d.rounded_rectangle([dx, dy, dx + dw, dy + dh], radius=int(dw * 0.30), fill=BRAND)


def make(size, radius_ratio, scale, maskable=False, bg=(TOP, BOT)):
    base = gradient(size, bg[0], bg[1]).convert("RGBA")
    if maskable:
        img = base
    else:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        img.paste(base, (0, 0), rounded_mask(size, radius_ratio))
    d = ImageDraw.Draw(img)
    draw_building(d, size, scale=scale)
    return img


jobs = [
    ("icon-192.png", 192, 0.22, 0.92, False),
    ("icon-512.png", 512, 0.22, 0.92, False),
    ("icon-maskable-192.png", 192, 0.5, 0.62, True),
    ("icon-maskable-512.png", 512, 0.5, 0.62, True),
    ("apple-touch-icon.png", 180, 0.0, 0.86, False),
    ("favicon-32.png", 32, 0.22, 0.94, False),
    ("favicon-16.png", 16, 0.22, 0.96, False),
]

for name, size, rr, sc, mask in jobs:
    img = make(size, rr, sc, maskable=mask)
    if name.startswith("apple-touch"):
        flat = Image.new("RGB", (size, size), TOP)
        flat.paste(img, (0, 0), img)
        flat.save(os.path.join(OUT, name), "PNG")
    else:
        img.save(os.path.join(OUT, name), "PNG")
    print("wrote", name, size)
