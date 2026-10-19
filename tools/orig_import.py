#!/usr/bin/env python3
"""Importer for the original Mega-Lo-Mania data files (supplied by the user, never committed).

* ILBM/LBM reader (BMHD, CMAP, BODY with ByteRun1) -> palette-index image
* MEGA.EXE text-table extractor (island names, epochs, ranks, elements, weapons)

Only formats that are fully understood are read. The proprietary .DAT files are not decoded
by anyone yet, so no map or balance data comes from them.
"""
import struct
from pathlib import Path


def _chunks(data):
    if data[:4] != b'FORM' or data[8:12] not in (b'ILBM', b'PBM '):
        raise ValueError('not an IFF ILBM')
    pos = 12
    end = 8 + struct.unpack('>I', data[4:8])[0]
    while pos + 8 <= min(end, len(data)):
        cid = data[pos:pos + 4]
        size = struct.unpack('>I', data[pos + 4:pos + 8])[0]
        yield cid, data[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)


def _unpack_byterun1(src, expect):
    out = bytearray()
    i = 0
    while len(out) < expect and i < len(src):
        n = src[i]
        i += 1
        if n < 128:
            out += src[i:i + n + 1]
            i += n + 1
        elif n > 128:
            out += bytes([src[i]]) * (257 - n)
            i += 1
    return bytes(out[:expect])


def load_ilbm(path):
    """Return (width, height, palette[(r,g,b)], pixels[list of rows of indices])."""
    data = Path(path).read_bytes()
    bmhd = cmap = body = None
    for cid, payload in _chunks(data):
        if cid == b'BMHD':
            bmhd = payload
        elif cid == b'CMAP':
            cmap = payload
        elif cid == b'BODY':
            body = payload
    if bmhd is None or body is None:
        raise ValueError('missing BMHD/BODY')
    w, h, _x, _y, planes, masking, comp = struct.unpack('>HHhhBBB', bmhd[:11])
    stride = ((w + 15) // 16) * 2
    nplanes = planes + (1 if masking == 1 else 0)
    raw = _unpack_byterun1(body, stride * nplanes * h) if comp == 1 else body
    pal = [tuple(cmap[i * 3:i * 3 + 3]) for i in range(len(cmap) // 3)] if cmap else []
    rows = []
    for y in range(h):
        base = y * stride * nplanes
        row = [0] * w
        for p in range(planes):
            line = raw[base + p * stride: base + (p + 1) * stride]
            for x in range(w):
                if line[x >> 3] & (0x80 >> (x & 7)):
                    row[x] |= 1 << p
        rows.append(row)
    return w, h, pal, rows


def read_strings(exe_path):
    """Printable ASCII strings of the DOS executable with their file offsets."""
    data = Path(exe_path).read_bytes()
    out, cur, start = [], bytearray(), 0
    for i, b in enumerate(data + b'\0'):
        if 32 <= b < 127:
            if not cur:
                start = i
            cur.append(b)
        else:
            if len(cur) >= 3:
                out.append((start, cur.decode('ascii')))
            cur = bytearray()
    return out


def exe_text_tables(exe_path):
    """Extract the evidenced text tables. Returns dict of lists plus 'offsets'."""
    strs = read_strings(exe_path)
    names = [s for _, s in strs]
    off = {s: o for o, s in strs}

    def run(first, last, upper=False):
        """Consecutive strings from `first` through `last` (exact matches)."""
        a = names.index(first)
        b = names.index(last, a)
        return names[a:b + 1], strs[a][0]
    islands, islands_off = run('Aloha', 'Zappa')
    epochs, epochs_off = run('1ST EPOCH', '9TH EPOCH')
    ranks, ranks_off = run('PRESIDENT', 'STALWART')
    elements, el_off = run('wood', 'alien')
    return {
        'islands': [n.upper() for n in islands],
        'finale': names[names.index('Megalomania')].upper(),
        'epochs': epochs,
        'ranks': ranks,
        'elements': [e.upper() for e in elements],
        'offsets': {'islands': islands_off, 'epochs': epochs_off, 'ranks': ranks_off, 'elements': el_off},
    }


if __name__ == '__main__':
    import json
    import sys
    print(json.dumps(exe_text_tables(sys.argv[1]), indent=1))
