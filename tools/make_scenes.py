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
    from vic_bitmap import convert
    return convert(im)


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
        from vic_bitmap import convert, mixed_story
        multicolor = 2 if 16 <= i <= 19 else int(i == 20)
        bitmap, screen, color, preview = mixed_story(im) if multicolor == 2 else convert(im, multicolor=bool(multicolor))
        frames = 180 if i <= 15 else 360
        data = encode(bitmap, screen, color, multicolor=multicolor, frames=frames)
        decode(data)
        file = f'SCENE{i:02d}'
        (out / (file + '.bin')).write_bytes(data)
        preview.save(out / (file + '.png'))
        manifest.append(dict(file=file, source=name, bytes=len(data), frames_pal=frames, multicolor=multicolor))
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
