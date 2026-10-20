#!/usr/bin/env python3
"""Convert the 28 original 48x16 atlas tiles to two C64 multicolour sprites each.

The row-major association with campaign slots is a port choice, not recovered map logic.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from orig_import import load_ilbm
from orig_convert import C64


def build(decoded, out):
    out.mkdir(parents=True,exist_ok=True)
    w,h,pal,rows=load_ilbm(decoded/'ISLANDS.LBM')
    if w<144 or h<160:raise ValueError('island atlas is too small')
    manifest=[]
    for island in range(28):
        left,top=(island%3)*48,(island//3)*16
        pixels=[[min(range(16),key=lambda c:sum((pal[rows[top+y][left+x]][k]-C64[c][k])**2 for k in range(3))) for x in range(48)] for y in range(16)]
        counts=Counter(c for row in pixels for c in row if c)
        colors=[c for c,_ in counts.most_common(3)]
        colors+=(3-len(colors))*[15]
        palette=[0]+colors
        blob=bytearray()
        for half in range(2):
            for y in range(21):
                value=0
                for x in range(12):
                    c=pixels[y-2][half*24+x*2] if 2<=y<18 else 0
                    code=min(range(4),key=lambda j:sum((C64[c][k]-C64[palette[j]][k])**2 for k in range(3)))
                    value=(value<<2)|code
                blob.extend(value.to_bytes(3,'big'))
            blob.append(0)
        # Sprite codes: 01 shared $D025, 10 per-sprite, 11 shared $D026.
        (out/f'ISL{island+1:02d}.bin').write_bytes(b'MLC1'+bytes(colors)+blob)
        manifest.append(dict(file=f'ISL{island+1:02d}',atlas_x=left,atlas_y=top,colors=colors))
    (out/'islands.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('28 island files, 135 bytes each')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--decoded',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();build(a.decoded,a.out)
