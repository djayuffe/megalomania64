#!/usr/bin/env python3
"""Generate the intro picture: a 160x200 C64 multicolour bitmap.

Outputs (committed, deterministic):
  assets/intro_bitmap.bin  8000 bytes  -> $6000
  assets/intro_screen.bin  1000 bytes  -> $5C00 (screen RAM: colours of %01 / %10)
  assets/intro_color.bin   1000 bytes  -> copied to $D800 (colour RAM: colour of %11)
  assets/intro_preview.png 320x200 palette-accurate render of those bytes (x2)
Background colour (%00) is global: black ($D021 = 0).
Rows 22-24 are the text band. The PRESS FIRE cells (row 22) use only %11, so the
game can colour-cycle them through colour RAM at run time.
Needs Pillow + DejaVu Sans Bold only when regenerating; the build uses the committed .bin files.
"""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PAL = [(0,0,0),(255,255,255),(104,55,43),(112,164,178),(111,61,134),(88,141,67),(53,40,121),(184,199,111),
       (111,79,37),(67,57,0),(154,103,89),(68,68,68),(108,108,108),(154,210,132),(108,94,181),(149,149,149)]
W, H = 160, 200
TEXT_ROW = 22                      # first row of the bottom text band (y = 176)
BAYER = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]

img = [[0]*W for _ in range(H)]

def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = c

def dither(x, y, a, b, t):
    """t in 0..1: fraction of b."""
    return b if (BAYER[y & 3][x & 3] + 0.5) / 16.0 < t else a

def band(x, y, stops):
    """Vertical gradient through (y0, colour) stops with ordered dither between neighbours."""
    for i in range(len(stops) - 1):
        (y0, c0), (y1, c1) = stops[i], stops[i + 1]
        if y0 <= y < y1:
            return dither(x, y, c0, c1, (y - y0) / float(y1 - y0))
    return stops[-1][1]

# ---- sky ------------------------------------------------------------------
HORIZON = 120
for y in range(0, HORIZON):
    for x in range(W):
        img[y][x] = band(x, y, [(0,0),(66,0),(84,6),(100,14),(112,4),(120,4)])
# stars
for (sx, sy) in [(6,4),(22,12),(37,3),(55,9),(71,5),(88,2),(102,11),(119,4),(137,8),(150,3),(13,26),(47,22),(96,24),(128,20),(154,27),(33,36),(112,33)]:
    put(sx, sy, 1)
for (sx, sy) in [(60,16),(144,16),(8,40)]:
    put(sx, sy, 15); put(sx+1, sy, 15)

# ---- sun ------------------------------------------------------------------
def ellipse(cx, cy, rx, ry, fn):
    for y in range(int(cy - ry), int(cy + ry) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= 1.0:
                c = fn(x, y, d)
                if c is not None:
                    put(x, y, c)
SUNX, SUNY = 78, 118
ellipse(SUNX, SUNY, 19, 32, lambda x, y, d: None if y >= HORIZON else (8 if d > 0.72 else 7))
# sun bands (cut-out stripes in the lower half)
for sy in (101, 105, 108, 111, 114, 117):
    for x in range(SUNX - 17, SUNX + 18):
        if img[sy][x] in (7, 8, 1):
            img[sy][x] = 4

# ---- volcano on the horizon -----------------------------------------------
def tri(cx, top, base, half, fn):
    for y in range(top, base):
        w = half * (y - top) / float(base - top)
        for x in range(int(cx - w), int(cx + w) + 1):
            c = fn(x, y, (x - cx) / max(w, 1))
            if c is not None:
                put(x, y, c)
tri(128, 84, HORIZON, 26, lambda x, y, u: 9 if u < 0.15 else (11 if u < 0.6 else 0))
tri(128, 84, 92, 6, lambda x, y, u: dither(x, y, 2, 7, 0.5) if abs(u) < 0.7 else None)   # lava glow in the crater
for (lx, ly) in [(125,95),(124,100),(126,106),(123,111)]:                                 # lava runs
    put(lx, ly, 2); put(lx, ly + 1, 10)
# smoke
for i, (px, py, r) in enumerate([(128,80,2),(131,74,3),(126,67,4),(132,58,5)]):
    ellipse(px, py, r, r * 0.8, lambda x, y, d: 12 if d > 0.5 else 15)

# ---- sea ------------------------------------------------------------------
for y in range(HORIZON, H):
    for x in range(W):
        img[y][x] = band(x, y, [(HORIZON,10),(126,14),(146,6),(176,6),(200,0)])
# wave streaks
import random
rnd = random.Random(64)
for y in range(HORIZON + 3, 176, 2):
    for _ in range(3 + (y - HORIZON) // 12):
        x = rnd.randrange(0, W); n = rnd.randrange(2, 4 + (y - HORIZON) // 8)
        for k in range(n):
            put(x + k, y, 3 if (y - HORIZON) < 30 else 14)
# sun glitter
for y in range(HORIZON + 2, 168, 2):
    half = 3 + (y - HORIZON) // 3
    half = min(half, 17)
    for x in range(SUNX - half, SUNX + half + 1):
        if rnd.random() < 0.45:
            put(x, y, 7 if (y - HORIZON) < 20 else 8)

# ---- foreground island (left) ----------------------------------------------
def hill(cx, cy, rx, ry, base_c, light_c, dark_c):
    ellipse(cx, cy, rx, ry, lambda x, y, d: (dark_c if (y > cy + ry * 0.35) else (light_c if (x < cx - rx * 0.2 and y < cy) else base_c)) if y < H else None)
hill(34, 186, 50, 20, 5, 13, 9)
hill(66, 188, 22, 12, 5, 13, 9)
hill(12, 184, 16, 10, 13, 13, 5)
# beach line
for x in range(0, 82):
    for y in range(166, 176):
        if img[y][x] in (5, 13, 9) and y > 171:
            img[y][x] = 7 if (x + y) & 1 else 8
# castle (grey keep with towers, red flag)
def rect(x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(x, y, c)
rect(27, 148, 41, 172, 12); rect(27, 148, 29, 172, 15); rect(39, 148, 41, 172, 11)
rect(22, 154, 27, 172, 12); rect(22, 154, 23, 172, 15)
rect(41, 154, 46, 172, 12); rect(45, 154, 46, 172, 11)
for x in range(27, 42, 3):
    rect(x, 145, x + 1, 147, 12)
for x in (22, 25): rect(x, 151, x + 1, 153, 12)
for x in (42, 45): rect(x, 151, x + 1, 153, 12)
rect(33, 162, 35, 172, 0); rect(34, 161, 34, 161, 0)   # gate
for y in (152, 157, 162):
    put(31, y, 0); put(37, y, 0)                        # arrow slits
for (fx, fy, fc) in [(34, 136, 2)]:
    rect(fx, fy - 2, fx, 146, 11)
    rect(fx + 1, fy - 2, fx + 6, fy + 2, fc)
    rect(fx + 1, fy + 3, fx + 4, fy + 3, fc)
# palm trees
def palm(x, y, h, lean):
    for i in range(h):
        put(x + int(lean * i / h), y - i, 8)
        put(x + 1 + int(lean * i / h), y - i, 9)
    tx, ty = x + lean, y - h
    for dx, dy in [(-7,2),(-5,-1),(-3,-3),(0,-4),(3,-3),(5,-1),(7,2),(-4,3),(4,3)]:
        n = max(abs(dx), abs(dy))
        for k in range(n + 1):
            put(tx + dx * k // n, ty + dy * k // n + (1 if abs(dx) > 4 and k > n // 2 else 0), 5 if k % 2 else 13)
    put(tx, ty, 8); put(tx + 1, ty + 1, 8)
palm(11, 178, 24, -2)
palm(58, 180, 20, 3)
palm(74, 183, 14, 2)

# ---- ships (right) ------------------------------------------------------------
def ship(x, y, sail_c, flag_c):
    rect(x - 7, y, x + 7, y + 1, 8)
    rect(x - 5, y + 2, x + 5, y + 2, 9)
    rect(x, y - 14, x, y - 1, 9)
    for i in range(0, 11):
        w = 6 - (i * 6) // 11
        rect(x + 1, y - 13 + i, x + 1 + w, y - 13 + i, sail_c)
    rect(x + 1, y - 16, x + 4, y - 15, flag_c)
    for k in range(-6, 8):
        put(x + k, y + 3, 14 if k & 1 else 3)
ship(112, 156, 1, 2)
ship(138, 170, 15, 7)
ship(100, 138, 1, 4)

# ---- logo -----------------------------------------------------------------------
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
def text_mask(text, size_font, width_hires=320, height=44):
    m = Image.new('L', (width_hires, height), 0)
    d = ImageDraw.Draw(m)
    bbox = d.textbbox((0, 0), text, font=size_font)
    d.text(((width_hires - (bbox[2] - bbox[0])) // 2 - bbox[0], (height - (bbox[3] - bbox[1])) // 2 - bbox[1]), text, font=size_font, fill=255)
    return m.resize((W, height), Image.BILINEAR)       # hires 2:1 -> multicolour pixels
def paint_logo(text, y0, f, big=True):
    m = text_mask(text, f, height=24)
    px = m.load()
    def on(x, y):
        return 0 <= x < W and 0 <= y < 24 and px[x, y] > 85
    for y in range(24):
        for x in range(W):
            pass
    for y in range(24):
        for x in range(W):
            if on(x, y):
                edge = not (on(x - 1, y) and on(x + 1, y) and on(x, y - 1) and on(x, y + 1))
                c = ((1 if y < 8 else (7 if y < 16 else 10)) if big else (3 if y < 12 else 14)) if not edge else (2 if big else 6)
                put(x, y0 + y, c)
f1 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 27)
paint_logo('MEGA-LO-MANIA', 0, f1)
f2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 17)
paint_logo('ISLAND WARS 64', 32, f2, big=False)
# gold rule under the logo
for x in range(10, 150):
    put(x, 58, 7 if x & 1 else 8)

# ---- text band (rows 22-24) -----------------------------------------------------
charset = (ROOT / 'assets/charset.bin').read_bytes()
for y in range(TEXT_ROW * 8, H):
    for x in range(W):
        img[y][x] = 0
def glyph_text(text, x0, y0, c):
    for i, ch in enumerate(text):
        g = charset[ord(ch) * 8:ord(ch) * 8 + 8]
        for gy in range(8):
            for gx in range(8):
                if g[gy] & (0x80 >> gx):
                    put(x0 + i * 8 + gx, y0 + gy, c)
def centre(text):
    return (W - len(text) * 8) // 2
glyph_text('PRESS FIRE OR KEY', centre('PRESS FIRE OR KEY'), TEXT_ROW * 8, 1)
glyph_text('UNOFFICIAL FAN GAME', centre('UNOFFICIAL FAN GAME'), (TEXT_ROW + 1) * 8, 12)
glyph_text('C64C EDITION V4.2', centre('C64C EDITION V4.2'), (TEXT_ROW + 2) * 8, 11)

# ---- convert to multicolour bitmap -----------------------------------------------
def dist(a, b):
    ra, rb = PAL[a], PAL[b]
    return sum((ra[i] - rb[i]) ** 2 for i in range(3))
bitmap = bytearray(8000); screen = bytearray(1000); color = bytearray(1000)
recon = [[0] * W for _ in range(H)]
for cy in range(25):
    for cx in range(40):
        cell = [[img[cy * 8 + y][cx * 4 + x] for x in range(4)] for y in range(8)]
        counts = {}
        for row in cell:
            for c in row:
                if c != 0:
                    counts[c] = counts.get(c, 0) + 1
        if cy == TEXT_ROW:                                  # cycling text row: %11 only
            chosen = [c for c, _ in sorted(counts.items(), key=lambda kv: -kv[1])][:1]
            code_of = {chosen[0]: 3} if chosen else {}
            color[cy * 40 + cx] = chosen[0] if chosen else 1
            screen[cy * 40 + cx] = 0
        else:
            chosen = [c for c, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))][:3]
            while len(chosen) < 3:
                chosen.append(chosen[-1] if chosen else 0)
            uniq = []
            for c in chosen:
                if c not in uniq:
                    uniq.append(c)
            a = uniq[0] if len(uniq) > 0 else 0
            b = uniq[1] if len(uniq) > 1 else a
            d3 = uniq[2] if len(uniq) > 2 else b
            screen[cy * 40 + cx] = (a << 4) | b
            color[cy * 40 + cx] = d3
            code_of = {}
            for code, c in ((1, a), (2, b), (3, d3)):
                code_of.setdefault(c, code)
        for y in range(8):
            byte = 0
            for x in range(4):
                c = cell[y][x]
                if c == 0:
                    code = 0
                elif c in code_of:
                    code = code_of[c]
                else:
                    best = min(list(code_of.keys()) + [0], key=lambda k: dist(c, k))
                    code = 0 if best == 0 else code_of[best]
                byte = (byte << 2) | code
                recon[cy * 8 + y][cx * 4 + x] = 0 if code == 0 else {1: (screen[cy*40+cx] >> 4), 2: (screen[cy*40+cx] & 15), 3: color[cy*40+cx]}[code]
            bitmap[(cy * 40 + cx) * 8 + y] = byte

(ROOT / 'assets/intro_bitmap.bin').write_bytes(bytes(bitmap))
(ROOT / 'assets/intro_screen.bin').write_bytes(bytes(screen))
(ROOT / 'assets/intro_color.bin').write_bytes(bytes(color))
out = Image.new('RGB', (W * 2, H), (0, 0, 0))
op = out.load()
for y in range(H):
    for x in range(W):
        for k in range(2):
            op[x * 2 + k, y] = PAL[recon[y][x]]
out.save(ROOT / 'assets/intro_preview.png')
print('wrote assets/intro_{bitmap,screen,color}.bin and intro_preview.png')
