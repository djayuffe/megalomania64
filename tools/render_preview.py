#!/usr/bin/env python3
"""Render deterministic C64 VIC-II memory snapshot for build inspection (not a screenshot of VICE)."""
import sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from cpu6502 import CPU
PALETTE=[(0,0,0),(255,255,255),(136,0,0),(170,255,238),(204,68,204),(0,204,85),(0,0,170),(238,238,119),(221,136,85),(102,68,0),(255,119,119),(51,51,51),(119,119,119),(170,255,102),(0,136,255),(187,187,187)]

def preview(out,scenario='start'):
 syms={v:int(k,16) for k,v in (line.split() for line in (ROOT/'dist/symbols.txt').read_text().splitlines())}
 cpu=CPU(ROOT/'dist/MegaLoMania64.prg');cpu.pc=syms['start']
 for _ in range(400000):
  if cpu.pc==syms['main_loop']:break
  cpu.step()
 else:raise RuntimeError('Boot never reached main loop')
 if scenario=='expansion':
  cpu.key=ord('D');cpu.call(syms['read_keys'])
  cpu.key=ord('X');cpu.call(syms['read_keys'])
  for _ in range(8):cpu.call(syms['simulate'])
 if scenario=='future':
  for key in ('L','2','8'):
   cpu.key=ord(key);cpu.call(syms['read_keys'])
  for _ in range(12):cpu.call(syms['simulate'])
 m=cpu.m;px=Image.new('RGB',(320,200),PALETTE[m[0xd021]&15]);pixels=px.load()
 bg=PALETTE[m[0xd021]&15];mc1=PALETTE[m[0xd022]&15];mc2=PALETTE[m[0xd023]&15]
 for r in range(25):
  for c in range(40):
   idx=r*40+c;code=m[0x400+idx];color=m[0xd800+idx]&15
   multi=bool((m[0xd016]&16) and (color&8))
   for y in range(8):
    data=m[0x3800+8*code+y]
    if multi:
     col=[bg,mc1,mc2,PALETTE[color&7]]
     for bx in range(4):
      v=(data>>(6-2*bx))&3
      pixels[c*8+bx*2,r*8+y]=col[v];pixels[c*8+bx*2+1,r*8+y]=col[v]
    else:
     for bx in range(8):
      pixels[c*8+bx,r*8+y]=PALETTE[color] if (data>>(7-bx))&1 else bg
 # Hardware sprite coordinates offset to bitmap visible character area
 if m[0xd015]&1:
  sx=m[0xd000]-24;sy=m[0xd001]-50
  for y in range(21):
   for bx in range(24):
    b=m[0x3700+y*3+(bx//8)]
    if b&(1<<(7-bx%8)) and 0<=sx+bx<320 and 0<=sy+y<200:
     pixels[sx+bx,sy+y]=PALETTE[m[0xd027]&15]
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);px.resize((960,600),Image.Resampling.NEAREST).save(out)
 print(f'Rendered memory-accurate reference: {out}')

if __name__=='__main__':
 preview(ROOT/'dist/preview_initial.png')
 preview(ROOT/'dist/preview_expansion.png','expansion')
 preview(ROOT/'dist/preview_future.png','future')
