#!/usr/bin/env python3
"""Down-convert the original Mega-Lo-Mania art to C64 data.

    python3 tools/orig_convert.py --orig original/

Inputs (user supplied, not in the repo):  MTARFLD.LBM (galaxy), ARMIES.LBM, BUILDS.LBM, MEGA.EXE
Outputs (committed, deterministic):
  assets/orig/galaxy_c64.png      160x200 palette-index backdrop in C64 colours (rows 58-175)
  assets/orig/army_frames.bin     10 epochs x 4 walk frames x 64 bytes (multicolour sprites)
  assets/orig/build_icons.bin     10 building icons x 64 bytes (multicolour sprites)
  assets/orig/samples.bin         4-bit packed samples (original Amiga 8SVX, 5 kHz) + samples.json index
  assets/orig/orig_text.json      island / epoch / rank / element names with EXE offsets
  assets/orig/sprites_preview.png palette-accurate preview of every converted sprite

Multicolour sprite colours: %01 = black ($D025), %10 = per-sprite colour (team), %11 = light grey ($D026).
The mapping of sheet rows to epochs is a design choice of this port, not recovered game data.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from orig_import import load_ilbm, exe_text_tables, load_8svx
import math

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/orig'
C64 = [(0,0,0),(255,255,255),(104,55,43),(112,164,178),(111,61,134),(88,141,67),(53,40,121),(184,199,111),
       (111,79,37),(67,57,0),(154,103,89),(68,68,68),(108,108,108),(154,210,132),(108,94,181),(149,149,149)]
BAYER = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]

# ---------------------------------------------------------------- galaxy backdrop
GAL_SRC_Y0, GAL_SRC_Y1 = 27, 228          # visible part of the picture
GAL_DST_Y0, GAL_DST_Y1 = 58, 176          # rows of the 160x200 bitmap it occupies
RAMP = [(0.0, 0), (0.14, 6), (0.40, 14), (0.72, 3), (0.93, 1)]   # brightness -> black/blue/lblue/cyan/white


def galaxy(orig):
    w, h, pal, rows = load_ilbm(orig / 'MTARFLD.LBM')
    dh = GAL_DST_Y1 - GAL_DST_Y0
    img = [[0] * 160 for _ in range(200)]
    for ty in range(dh):
        sy0 = GAL_SRC_Y0 + ty * (GAL_SRC_Y1 - GAL_SRC_Y0) / dh
        sy1 = GAL_SRC_Y0 + (ty + 1) * (GAL_SRC_Y1 - GAL_SRC_Y0) / dh
        ya, yb = int(sy0), max(int(sy0) + 1, int(round(sy1)))
        for tx in range(160):
            vals = [max(pal[rows[y][x]]) / 255.0 for y in range(ya, yb) for x in (tx * 2, tx * 2 + 1)]
            v = 0.5 * sum(vals) / len(vals) + 0.5 * max(vals)         # keep the stars alive
            img[GAL_DST_Y0 + ty][tx] = ramp(v, tx, GAL_DST_Y0 + ty)
    return img


def ramp(v, x, y):
    for i in range(len(RAMP) - 1, -1, -1):
        lo, c = RAMP[i]
        if v >= lo:
            if i + 1 < len(RAMP):
                hi = RAMP[i + 1][0]
                t = (v - lo) / (hi - lo)
                return RAMP[i + 1][1] if (BAYER[y & 3][x & 3] + 0.5) / 16.0 < t * 0.9 else c
            return c
    return 0


def write_galaxy_png(img):
    from PIL import Image
    im = Image.new('P', (160, 200))
    flat = []
    for r, g, b in C64:
        flat += [r, g, b]
    im.putpalette(flat + [0] * (768 - len(flat)))
    im.putdata([c for row in img for c in row])
    im.save(OUT / 'galaxy_c64.png')


# ---------------------------------------------------------------- samples (original Amiga 8SVX)
SMP_RATE = 5000                      # playback rate of the C64 NMI player (Hz)
# (key, carved file id on the Amiga disk, seconds kept, gain into the limiter)
SAMPLES = [('stick', '00cda00', 0.18, 1.0), ('throw', '00c6e00', 0.19, 1.0), ('musket', '00c6800', 0.09, 1.0),
           ('machinegun', '00c3400', 0.095, 1.0), ('cannon', '00c3a00', 0.40, 1.0), ('missile', '00c7e00', 0.50, 1.0),
           ('laser', '00d0800', 0.30, 1.0), ('explosion', '00c9e00', 0.45, 1.0), ('grunt', '00cfc00', 0.28, 1.0),
           ('orchestra', '0050a00', 0.50, 1.0), ('timpani', '0066600', 0.375, 1.0)]


def sample_nibbles(orig, fid, seconds, gain):
    source = orig / 'amiga_8svx' / f'original_{fid}_8SVX.iff'
    if not source.is_file():source = orig / f'{int(fid,16):06x}_8SVX.iff'
    rate, name, pcm = load_8svx(source)
    n_out = int((len(pcm) / rate if seconds is None else seconds) * SMP_RATE)
    step = rate / SMP_RATE
    mean = sum(pcm) / len(pcm)
    out = []
    for k in range(n_out):
        a, b = k * step, (k + 1) * step
        i0, i1 = int(a), min(len(pcm), max(int(a) + 1, int(math.ceil(b))))
        seg = pcm[i0:i1] if i0 < len(pcm) else [mean]
        out.append(sum(seg) / len(seg) - mean)
    peak = max(abs(v) for v in out) or 1.0
    q, err, res = 1.6 * gain, 0.0, []
    for k, v in enumerate(out):
        y = math.tanh(q * v / peak) / math.tanh(q)
        fade = min(1.0, (k + 1) / 4.0, (n_out - k) / 6.0)
        t = 8.0 + 7.4 * y * fade + err
        c = max(0, min(15, int(round(t))))
        err = max(-1.0, min(1.0, t - c))
        res.append(c)
    if len(res) & 1:
        res.append(8)
    return name, res


def samples(orig):
    blob = bytearray()
    index = []
    for key, fid, secs, gain in SAMPLES:
        name, nib = sample_nibbles(orig, fid, secs, gain)
        index.append({'key': key, 'original_name': name, 'carve': fid, 'offset': len(blob), 'nibbles': len(nib), 'rate': SMP_RATE})
        for i in range(0, len(nib), 2):
            blob.append((nib[i] << 4) | nib[i + 1])
    return bytes(blob), index


# ---------------------------------------------------------------- sprites
T, BLK, TEAM, GREY = 0, 1, 2, 3          # multicolour sprite codes


def classify(rgb, bg, dark=80):
    r, g, b = rgb
    if rgb == bg or (g > r + 24 and g > b + 24 and max(rgb) < 130):          # background / green shadow
        return T
    lum = (r * 3 + g * 6 + b) / 10
    if max(rgb) - min(rgb) >= 44 and lum >= 45:
        return TEAM                      # coloured clothing / brick / roofs
    if lum < dark:
        return BLK
    return GREY


def sheet_classes(pal, rows, bgidx, dark=80):
    bg = pal[bgidx]
    return [[classify(pal[i], bg, dark) for i in row] for row in rows]


def vote(cls, x0, y0, kx, ky):
    """Class of the source block [x0,x0+kx) x [y0,y0+ky) (floats ok)."""
    counts = [0.0, 0.0, 0.0, 0.0]
    for y in range(int(y0), max(int(y0) + 1, int(round(y0 + ky)))):
        for x in range(int(x0), max(int(x0) + 1, int(round(x0 + kx)))):
            if 0 <= y < len(cls) and 0 <= x < len(cls[0]):
                counts[cls[y][x]] += 1
    n = sum(counts)
    if n == 0 or counts[T] > 0.6 * n:
        return T
    weight = {BLK: 0.65, TEAM: 1.0, GREY: 1.0}
    return max((BLK, TEAM, GREY), key=lambda c: counts[c] * weight[c])


def pack(grid):
    """grid[21][12] of codes -> 64 bytes."""
    out = bytearray()
    for y in range(21):
        row = grid[y]
        for b in range(3):
            v = 0
            for k in range(4):
                v = (v << 2) | row[b * 4 + k]
            out.append(v)
    out.append(0)
    return bytes(out)


def blank():
    return [[T] * 12 for _ in range(21)]


# epoch -> (row, first column) of a 16x16 walk-frame strip in ARMIES.LBM (assignment is this port's)
# (row, first column, column stride); stride 2 over an 8-frame strip gives a 4-frame cycle
ARMY_STRIPS = [(0, 0, 2), (4, 0, 2), (2, 0, 2), (6, 0, 2), (6, 8, 2), (9, 0, 2), (11, 0, 2), (12, 8, 2), (15, 14, 1), (12, 9, 2)]


def army_frames(orig):
    w, h, pal, rows = load_ilbm(orig / 'ARMIES.LBM')
    cls = sheet_classes(pal, rows, rows[0][0])
    data = bytearray()
    for row, col0, stride in ARMY_STRIPS:
        for f in range(4):
            sx = (col0 + f * stride) * 16
            sy = row * 16
            g = blank()
            for ty in range(16):
                for tx in range(8):
                    g[2 + ty][2 + tx] = vote(cls, sx + tx * 2, sy + ty, 2, 1)
            data += pack(g)
    return bytes(data)


def bbox(cls, x0, y0, x1, y1):
    xs = [x for y in range(y0, y1) for x in range(x0, x1) if cls[y][x]]
    ys = [y for y in range(y0, y1) for x in range(x0, x1) if cls[y][x]]
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1) if xs else None


def building_icons(orig):
    w, h, pal, rows = load_ilbm(orig / 'BUILDS.LBM')
    cls = sheet_classes(pal, rows, rows[0][319], dark=46)   # dark stone reads as grey, not as outline
    data = bytearray()
    cells = []
    for r in range(10):
        for c in range(4):
            bb = bbox(cls, c * 64, r * 60, c * 64 + 64, r * 60 + 60)
            if bb and (bb[2] - bb[0]) * (bb[3] - bb[1]) > 600:
                cells.append(bb)
                break
        else:
            cells.append(None)
    for bb in cells:
        g = blank()
        if bb:
            bw, bh = bb[2] - bb[0], bb[3] - bb[1]
            s = max(bw / 24.0, bh / 21.0)
            tw, th = int(bw / s / 2.0 + 0.5), int(bh / s + 0.5)
            ox, oy = (12 - tw) // 2, (21 - th) // 2
            for ty in range(th):
                for tx in range(tw):
                    g[oy + ty][ox + tx] = vote(cls, bb[0] + tx * s * 2, bb[1] + ty * s, s * 2, s)
        data += pack(g)
    return bytes(data)


def unpack_frame(blob):
    return [[(blob[y * 3 + b] >> (6 - 2 * k)) & 3 for b in range(3) for k in range(4)] for y in range(21)]


def preview(army, builds):
    from PIL import Image
    col = {T: (0, 0, 170), BLK: (0, 0, 0), TEAM: (88, 141, 67), GREY: (187, 187, 187)}
    cell = 28
    im = Image.new('RGB', (4 * cell * 2 + 8, 10 * cell + 4), (0, 0, 170))
    px = im.load()
    def blit(blob, ox, oy):
        g = unpack_frame(blob)
        for y in range(21):
            for x in range(12):
                for k in range(2):
                    px[ox + x * 2 + k, oy + y] = col[g[y][x]]
    for e in range(10):
        for f in range(4):
            blit(army[(e * 4 + f) * 64:(e * 4 + f + 1) * 64], f * cell, e * cell)
        blit(builds[e * 64:(e + 1) * 64], 4 * cell + 8, e * cell)
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(OUT / 'sprites_preview.png')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orig', default=str(ROOT / 'original'))
    ap.add_argument('--samples-only', action='store_true', help='rebuild effects from recovered Amiga IFFs without changing art')
    ap.add_argument('--effects-out', type=Path, help='write optional full-length original effect bank outside source checkout')
    a = ap.parse_args()
    orig = Path(a.orig)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.samples_only:
        blob,index=samples(orig)
        if a.effects_out:
            from scene_format import pack as rle_pack
            full=bytearray()
            for entry,(_,fid,_,gain) in zip(index,SAMPLES):
                _,nib=sample_nibbles(orig,fid,None,gain)
                entry['full_offset']=len(full);entry['full_nibbles']=len(nib)
                full.extend((nib[i]<<4)|nib[i+1] for i in range(0,len(nib),2))
            if len(full)>9000+3072:raise ValueError('full effect bank exceeds resident RAM')
            full.extend(bytes(9000+3072-len(full)))
            a.effects_out.mkdir(parents=True,exist_ok=True)
            (a.effects_out/'EFFECTS.bin').write_bytes(b'MLF1'+rle_pack(full[:9000])+rle_pack(full[9000:]))
        (OUT/'samples.bin').write_bytes(blob)
        (OUT/'samples.json').write_text(json.dumps({'rate':SMP_RATE,'samples':index},indent=1))
        print('samples:',len(index),len(blob),'bytes');return
    write_galaxy_png(galaxy(orig))
    army = army_frames(orig)
    builds = building_icons(orig)
    (OUT / 'army_frames.bin').write_bytes(army)
    (OUT / 'build_icons.bin').write_bytes(builds)
    t = exe_text_tables(orig / 'MEGA.EXE')
    (OUT / 'orig_text.json').write_text(json.dumps(t, indent=1))
    preview(army, builds)
    if (orig / 'amiga_8svx').is_dir():
        blob, index = samples(orig)
        (OUT / 'samples.bin').write_bytes(blob)
        (OUT / 'samples.json').write_text(json.dumps({'rate': SMP_RATE, 'samples': index}, indent=1))
        print('samples:', len(index), len(blob), 'bytes')
    print('wrote', ', '.join(sorted(p.name for p in OUT.iterdir())))


if __name__ == '__main__':
    main()
