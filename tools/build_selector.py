#!/usr/bin/env python3
"""Build a separate scene/island selector without changing the frozen intro."""
import hashlib,json,struct
from pathlib import Path
from asm6502 import Assembler
ROOT=Path(__file__).resolve().parents[1]
def build(content,target):
    symbols={name:int(at,16)for at,name in [line.split()for line in(ROOT/'dist/symbols.txt').read_text().splitlines()]}
    a=Assembler(ROOT/'src/gameplay/selector.asm');a.sym.update(symbols)
    overlay=target.with_suffix('.overlay.prg');a.assemble(overlay)
    if a.sym['sel_end']>0x2000:raise ValueError('selector overwrites resident intro support')
    original=(ROOT/'dist/MegaLoMania64.prg').read_bytes();raw=bytearray(original)
    patch=overlay.read_bytes();start=struct.unpack_from('<H',patch)[0];base=struct.unpack_from('<H',raw)[0]
    raw[2+start-base:2+start-base+len(patch)-2]=patch[2:]
    latest=0;bases=[]
    for i in range(29):
        header=(content/f'SCENE{i+1:02d}.bin').read_bytes()
        if header[:4]!=b'MLI1':raise ValueError('invalid scene stream')
        if header[4]!=4:latest=i
        bases.append(latest)
    at=2+a.sym['sel_bases']-base;raw[at:at+29]=bytes(bases)
    target.write_bytes(raw);overlay.unlink()
    report=dict(file=target.name,entry=a.sym['sel_start'],overlay_end=a.sym['sel_end'],intro_scenes=29,gameplay_islands=28,scene_bases=bases,frozen_entry_sha256=hashlib.sha256(original).hexdigest(),sha256=hashlib.sha256(raw).hexdigest(),symbols={k:v for k,v in a.sym.items()if k.startswith('sel_')})
    target.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    import argparse
    from check_intro import verify as verify_intro
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--content',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.resolve().is_relative_to(ROOT):raise ValueError('keep original-derived selector outside checkout')
    verify_intro(a.content);a.out.parent.mkdir(parents=True,exist_ok=True);print(json.dumps(build(a.content,a.out),indent=2))
