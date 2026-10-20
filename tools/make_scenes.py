#!/usr/bin/env python3
"""Convert decoded original cards/story/title to C64 disk scenes.

Credit framing and scene durations are port choices, not recovered DOS timing.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from PIL import Image
from orig_import import load_ilbm
from orig_convert import C64
from scene_format import encode, decode

ROOT = Path(__file__).resolve().parents[1]
SCENES = [f'V{i}E.DAT' for i in range(5, 20)] + [f'V{i}E.DAT' for i in range(1, 5)] + ['VH.DAT']


def image(path):
    w, h, palette, rows = load_ilbm(path)
    im = Image.new('RGB', (w, h))
    im.putdata([palette[index] for row in rows for index in row])
    return im


def frame(im, credits):
    if credits:
        box = im.getbbox()
        if box:
            im = im.crop((0, max(0, (box[1] + box[3]) // 2 - 100), 320,
                          max(0, (box[1] + box[3]) // 2 - 100) + 200))
    return im.resize((320, 200), Image.Resampling.LANCZOS)


def hires(im):
    # Preserve 320-pixel lettering; select the two most common mapped colours per VIC cell.
    nearest = {}
    indices = []
    for rgb in im.getdata():
        if rgb not in nearest:
            nearest[rgb] = min(range(16), key=lambda i: sum((rgb[k] - C64[i][k]) ** 2 for k in range(3)))
        indices.append(nearest[rgb])
    bitmap, screen = bytearray(), bytearray()
    preview = Image.new('RGB', (320, 200))
    for cy in range(25):
        for cx in range(40):
            cell = [indices[(cy * 8 + y) * 320 + cx * 8 + x] for y in range(8) for x in range(8)]
            colors = [c for c, _ in Counter(cell).most_common(2)]
            if len(colors) == 1:
                colors.append(colors[0])
            bg, fg = colors
            screen.append((fg << 4) | bg)
            mapped = {c: int(sum((C64[c][k] - C64[fg][k]) ** 2 for k in range(3)) <
                             sum((C64[c][k] - C64[bg][k]) ** 2 for k in range(3))) for c in set(cell)}
            for y in range(8):
                value = 0
                for x in range(8):
                    bit = mapped[cell[y * 8 + x]]
                    value = (value << 1) | bit
                    preview.putpixel((cx * 8 + x, cy * 8 + y), C64[fg if bit else bg])
                bitmap.append(value)
    return bytes(bitmap), bytes(screen), bytes(1000), preview


def build(decoded, dos, out):
    decoded, dos, out = Path(decoded), Path(dos), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, name in enumerate(SCENES, 1):
        if name == 'VH.DAT':
            raw = (decoded / 'MUNRISE.DAT').read_bytes()
            exe = (dos / 'MEGA.EXE').read_bytes()
            pal = [tuple(v * 255 // 63 for v in exe[j:j + 3]) for j in range(0x3326, 0x3356, 3)]
            if len(raw) != 32000 or any(v > 63 for v in exe[0x3326:0x3356]):
                raise ValueError('unexpected sunrise/executable layout')
            im = Image.new('RGB', (320, 200))
            im.putdata([pal[c] for b in raw for c in (b >> 4, b & 15)])
            logo = image(decoded / name).crop((0, 0, 320, 45))
            im.paste(logo, (0, 12), logo.convert('L').point(lambda x: 255 if x else 0))
        else:
            im = frame(image(decoded / name), i <= 15)
        bitmap, screen, color, preview = hires(im)
        frames = 180 if i <= 15 else 360
        data = encode(bitmap, screen, color, frames=frames)
        decode(data)
        file = f'SCENE{i:02d}'
        (out / (file + '.bin')).write_bytes(data)
        preview.save(out / (file + '.png'))
        manifest.append(dict(file=file, source=name, bytes=len(data), frames_pal=frames))
    # Restore the embedded v4 title after the streamed banks have been used.
    data = encode((ROOT / 'assets/intro_bitmap.bin').read_bytes(),
                  (ROOT / 'assets/intro_screen.bin').read_bytes(),
                  (ROOT / 'assets/intro_color.bin').read_bytes(), multicolor=True, frames=1)
    (out / 'TITLE.bin').write_bytes(data)
    (out / 'scenes.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{len(manifest)} original scenes + TITLE: {sum((out/(entry["file"]+".bin")).stat().st_size for entry in manifest)+len(data)} bytes')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--decoded', required=True, type=Path)
    p.add_argument('--dos', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    build(a.decoded, a.dos, a.out)
