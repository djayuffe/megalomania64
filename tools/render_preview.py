#!/usr/bin/env python3
"""Render deterministic C64 VIC-II memory snapshot for build inspection (not a screenshot of VICE)."""
import sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from cpu6502 import CPU
from common import boot
PALETTE=[(0,0,0),(255,255,255),(136,0,0),(170,255,238),(204,68,204),(0,204,85),(0,0,170),(238,238,119),(221,136,85),(102,68,0),(255,119,119),(51,51,51),(119,119,119),(170,255,102),(0,136,255),(187,187,187)]

def preview(out,scenario='start'):
 syms={v:int(k,16) for k,v in (line.split() for line in (ROOT/'dist/symbols.txt').read_text().splitlines())}
 cpu=CPU(ROOT/'dist/MegaLoMania64.prg')
 if scenario=='title':
  cpu.m[0x02a6]=1;cpu.pc=syms['start'];seen=[0]
  def stop(c):
   if c.pc==syms['title_wait']:seen[0]+=1
   if seen[0]>=340:raise StopIteration
  try:cpu.run_until(syms['main_loop'],on_pc=stop)
  except StopIteration:pass
 else:boot(cpu,syms)
 if scenario=='expansion':
  cpu.key=ord('D');cpu.call(syms['read_keys'])
  cpu.key=ord('X');cpu.call(syms['read_keys'])
  for _ in range(8):cpu.call(syms['simulate'])
 if scenario=='truce':
  cpu.key=ord('S');cpu.call(syms['read_keys'])   # selection onto a rival after moving
  cpu.m[syms['selected']]=11;cpu.key=ord('E');cpu.call(syms['read_keys']);cpu.call(syms['panel_values'])
 if scenario=='future':
  for key in ('L','2','8'):
   cpu.key=ord(key);cpu.call(syms['read_keys'])
  for _ in range(12):cpu.call(syms['simulate'])
 m=cpu.m;px=Image.new('RGB',(320,200),PALETTE[m[0xd021]&15]);pixels=px.load()
 bg=PALETTE[m[0xd021]&15];mc1=PALETTE[m[0xd022]&15];mc2=PALETTE[m[0xd023]&15]
 bitmap=bool(m[0xd011]&0x20)
 if bitmap:                      # multicolour bitmap in VIC bank 1 (intro picture)
  base=0x4000+((m[0xd018]>>3)&1)*0x2000;scr=0x4000+((m[0xd018]>>4)&15)*0x400
  for r in range(25):
   for c in range(40):
    idx=r*40+c;a=m[scr+idx];col=[bg,PALETTE[a>>4],PALETTE[a&15],PALETTE[m[0xd800+idx]&15]]
    for y in range(8):
     data=m[base+idx*8+y]
     for bx in range(4):
      v=(data>>(6-2*bx))&3
      pixels[c*8+bx*2,r*8+y]=col[v];pixels[c*8+bx*2+1,r*8+y]=col[v]
 for r in range(0 if bitmap else 25):
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
 if m[0xd015]&2:
  sx=m[0xd002]-24;sy=m[0xd003]-50
  for y in range(21):
   for bx in range(24):
    b=m[0x3740+y*3+(bx//8)]
    if b&(1<<(7-bx%8)) and 0<=sx+bx<320 and 0<=sy+y<200:
     pixels[sx+bx,sy+y]=PALETTE[m[0xd028]&15]
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);px.resize((960,600),Image.Resampling.NEAREST).save(out)
 print(f'Rendered memory-accurate reference: {out}')

if __name__=='__main__':
 preview(ROOT/'dist/preview_title.png','title')
 preview(ROOT/'dist/preview_initial.png')
 preview(ROOT/'dist/preview_truce.png','truce')
 preview(ROOT/'dist/preview_expansion.png','expansion')
 preview(ROOT/'dist/preview_future.png','future')
