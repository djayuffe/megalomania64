#!/usr/bin/env python3
"""Convert eight decoded DOS voice clips to a resident 4-bit / 4 kHz bank."""
import argparse
import json
import math
import struct
from pathlib import Path
from orig_import import load_8svx
from scene_format import pack

CLIPS = ['ARCONQ','FDEST','DESREADY','AWANNA','PVERYW','NOWAY','LAFF','ARWON']
FIRST, SECOND = 0x3380, 0x1ffa
RATE = 4000


def convert(path):
    rate, name, pcm = load_8svx(path)
    count = int(len(pcm) * RATE / rate) & ~1
    mean = sum(pcm) / len(pcm)
    values = []
    for i in range(count):
        a, b = i * rate // RATE, max(i * rate // RATE + 1, (i + 1) * rate // RATE)
        values.append(sum(pcm[a:b]) / len(pcm[a:b]) - mean)
    peak = max(map(abs, values)) or 1
    error, nibbles = 0.0, []
    for i, value in enumerate(values):
        fade = min(1.0, (i + 1) / 8, (count - i) / 8)
        target = 8 + 7 * math.tanh(1.5 * value / peak) / math.tanh(1.5) * fade + error
        nibble = max(0,min(15,round(target)));error=target-nibble;nibbles.append(nibble)
    return bytes((nibbles[i] << 4) | nibbles[i+1] for i in range(0,count,2)), name


def build(decoded, out):
    out.mkdir(parents=True,exist_ok=True)
    data, index, rows = bytearray(), bytearray(), []
    for source in CLIPS:
        packed, name = convert(decoded / source)
        offset = len(data)
        address = 0x4c80 + offset if offset < FIRST else 0xe000 + offset - FIRST
        index.extend(struct.pack('<HH',address,len(packed)*2));data.extend(packed)
        rows.append(dict(source=source,name=name,address=address,nibbles=len(packed)*2))
    if len(data) > FIRST + SECOND:
        raise ValueError('voice bank exceeds available RAM')
    data.extend(bytes(FIRST+SECOND-len(data)))
    file = b'MLV1' + index + pack(data[:FIRST]) + pack(data[FIRST:])
    (out/'SPEECH.bin').write_bytes(file)
    (out/'speech.json').write_text(json.dumps(dict(rate=RATE,clips=rows),indent=2)+'\n')
    print(f'Voice bank: {len(file)} disk bytes, {sum(r["nibbles"]//2 for r in rows)} sample bytes')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--decoded',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();build(a.decoded,a.out)
