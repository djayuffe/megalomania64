#!/usr/bin/env python3
"""Build/verify standard 35-track D64 images with PRG and sequential content files."""
from pathlib import Path
import argparse
import math
ROOT = Path(__file__).resolve().parents[1]
SECTORS = lambda t: 21 if t <= 17 else (19 if t <= 24 else (18 if t <= 30 else 17))
OFFSET = lambda t, s: 256 * (sum(SECTORS(i) for i in range(1, t)) + s)
SIZE = sum(SECTORS(i) for i in range(1, 36)) * 256


def cbm_name(name):
    if not name or len(name) > 16 or not name.isascii() or any(c in name for c in ':,*?@='):
        raise ValueError('invalid CBM filename')
    return name.upper().encode('ascii')


def make_image(prg, dest, filename='MEGALOMANIA', files=None):
    data = Path(prg).read_bytes()
    if len(data) < 2 or data[:2] != b'\x01\x08':
        raise ValueError('requires BASIC-loadable $0801 PRG')
    entries = [(filename, data, 0x82)] + [(n, bytes(b), 0x81) for n, b in (files or {}).items()]
    names = [cbm_name(n) for n, _, _ in entries]
    if len(set(names)) != len(names):
        raise ValueError('duplicate CBM filename')
    dirs = math.ceil(len(entries) / 8)
    if dirs > 18:
        raise ValueError('directory full')
    slots = []
    for t in range(1, 36):
        if t == 18:
            continue
        free = set(range(SECTORS(t)))
        s = 0
        while free:
            while s not in free:
                s = (s + 1) % SECTORS(t)
            slots.append((t, s)); free.remove(s)
            s = (s + 10) % SECTORS(t)
    counts = [max(1, math.ceil(len(b) / 254)) for _, b, _ in entries]
    if sum(counts) > len(slots):
        raise ValueError('files will not fit on D64')
    used = {(18, s) for s in range(dirs + 1)} | set(slots[:sum(counts)])
    disk, cursor = bytearray(SIZE), 0
    for index, ((name, payload, kind), blocks) in enumerate(zip(entries, counts)):
        chain = slots[cursor:cursor + blocks]; cursor += blocks
        for i, (t, s) in enumerate(chain):
            pos = OFFSET(t, s); chunk = payload[i * 254:(i + 1) * 254]
            disk[pos:pos + 2] = bytes(chain[i + 1] if i + 1 < blocks else (0, len(chunk) + 1))
            disk[pos + 2:pos + 2 + len(chunk)] = chunk
        dire = OFFSET(18, 1 + index // 8) + (index % 8) * 32
        disk[dire + 2] = kind
        disk[dire + 3:dire + 5] = bytes(chain[0])
        disk[dire + 5:dire + 21] = names[index].ljust(16, b'\xa0')
        disk[dire + 30:dire + 32] = blocks.to_bytes(2, 'little')
    for i in range(dirs):
        pos = OFFSET(18, i + 1)
        disk[pos:pos + 2] = bytes((18, i + 2) if i + 1 < dirs else (0, 255))
    bam = OFFSET(18, 0)
    disk[bam:bam + 4] = bytes((18, 1, 65, 0))
    for t in range(1, 36):
        free = [s for s in range(SECTORS(t)) if (t, s) not in used]
        b = bam + 4 + (t - 1) * 4
        disk[b] = len(free)
        for s in free:
            disk[b + 1 + s // 8] |= 1 << (s % 8)
    disk[bam + 0x90:bam + 0xa0] = b'MEGALOMANIA64'.ljust(16, b'\xa0')
    disk[bam + 0xa2:bam + 0xa7] = b'M5\xa02A'
    dest = Path(dest); dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(disk)
    recovered = read_files(dest)
    if recovered != {n.upper(): b for n, b, _ in entries}:
        raise ValueError('D64 payload verification failed')
    return counts[0]


def read_files(image):
    disk = Path(image).read_bytes()
    if len(disk) != SIZE:
        raise ValueError('not a 35-track D64 image')
    used, files = {(18, 0)}, {}

    def sector(t, s):
        if not 1 <= t <= 35 or not 0 <= s < SECTORS(t) or (t, s) in used:
            raise ValueError('invalid, overlapping or cyclic sector chain')
        used.add((t, s))
        return disk[OFFSET(t, s):OFFSET(t, s) + 256]

    bam = OFFSET(18, 0)
    t, s = disk[bam:bam + 2]
    directory = []
    while t:
        if t != 18:
            raise ValueError('directory outside track 18')
        b = sector(t, s)
        directory.extend(b[i:i + 32] for i in range(0, 256, 32) if b[i + 2])
        t, s = b[:2]
    if not directory or directory[0][2] != 0x82:
        raise ValueError('directory lacks boot PRG')
    for entry in directory:
        if entry[2] not in (0x81, 0x82):
            raise ValueError('unsupported/unclosed file type')
        name = entry[5:21].rstrip(b'\xa0').decode('ascii')
        if name in files:
            raise ValueError('duplicate directory entry')
        t, s = entry[3:5]; out, blocks = bytearray(), 0
        while t:
            b = sector(t, s); blocks += 1
            nt, ns = b[:2]; count = 254 if nt else ns - 1
            if not 0 <= count <= 254:
                raise ValueError('invalid final byte count')
            out.extend(b[2:2 + count]); t, s = nt, ns
        if blocks != int.from_bytes(entry[30:32], 'little'):
            raise ValueError('file block count mismatch')
        files[name] = bytes(out)
    for t in range(1, 36):
        b = bam + 4 + (t - 1) * 4
        free = [s for s in range(SECTORS(t)) if disk[b + 1 + s // 8] & (1 << (s % 8))]
        if len(free) != disk[b] or set(free) != {s for s in range(SECTORS(t)) if (t, s) not in used}:
            raise ValueError('BAM allocation mismatch')
    return files


def verify_image(image, original=None):
    payload = next(iter(read_files(image).values()))
    if original is not None and payload != original:
        raise ValueError('sector-chain payload differs from PRG')
    return payload


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--input', default=str(ROOT / 'dist/MegaLoMania64.prg'))
    p.add_argument('--output', default=str(ROOT / 'dist/MegaLoMania64.d64')); args = p.parse_args()
    n = make_image(args.input, args.output)
    print(f'PASS: {args.output} ({SIZE} bytes, {n} PRG blocks)')
