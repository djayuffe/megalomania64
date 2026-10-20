#!/usr/bin/env python3
"""Deterministic assembler-only build; needs neither Pillow nor an external assembler.

  python3 tools/build.py [--test] [--preview] [--regen-gfx] [--package]
"""
from pathlib import Path
import argparse,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))

def run_tests():
 result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (ROOT/'dist/build_test_log.txt').write_text(result.stdout)
 print(result.stdout,end='')
 if result.returncode:raise SystemExit(f'Tests failed: {result.returncode}')

def symbol(table,name):
 return int(next(row.split()[0] for row in table.splitlines() if row.split()[1]==name),16)

def main():
 p=argparse.ArgumentParser(description='Build Mega-Lo-Mania 64 (C64/C64C)')
 p.add_argument('--test',action='store_true',help='run the 6502-model test suite')
 p.add_argument('--regen-gfx',action='store_true',help='rebuild charset/cursor assets; requires Pillow')
 p.add_argument('--preview',action='store_true',help='render memory previews to dist/*.png; requires Pillow')
 p.add_argument('--package',action='store_true',help='also write the release ZIP and checksums')
 p.add_argument('--content',type=Path,help='generated original scene directory')
 p.add_argument('--full-d64',type=Path,help='output D64 including optional original content')
 a=p.parse_args()
 if bool(a.content)!=bool(a.full_d64):p.error('--content and --full-d64 must be used together')
 if a.full_d64 and a.full_d64.resolve().is_relative_to(ROOT):p.error('write the full D64 outside the source checkout')
 (ROOT/'dist').mkdir(exist_ok=True)
 if a.regen_gfx:
  subprocess.run([sys.executable,str(ROOT/'tools/make_gfx.py')],cwd=ROOT,check=True)
  subprocess.run([sys.executable,str(ROOT/'tools/make_intro.py')],cwd=ROOT,check=True)
 subprocess.run([sys.executable,str(ROOT/'tools/make_sprites.py')],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
 subprocess.run([sys.executable,str(ROOT/'tools/gen_tables.py')],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
 for name,expected in (('charset.bin',2048),('cursor_sprite.bin',64),('source_sprite.bin',64),('intro_bitmap.bin',8000),('intro_screen.bin',1000),('intro_color.bin',1000)):
  f=ROOT/'assets'/name
  if not f.is_file() or f.stat().st_size!=expected:raise SystemExit(f'Asset missing/invalid: {f}')
 output=ROOT/'dist/MegaLoMania64.prg'
 subprocess.run([sys.executable,str(ROOT/'tools/asm6502.py'),str(ROOT/'src/main.asm'),'-o',str(output),'--symbols',str(ROOT/'dist/symbols.txt')],cwd=ROOT,check=True)
 from make_d64 import make_image
 d64=ROOT/'dist/MegaLoMania64.d64'
 block_count=make_image(output,d64)
 print(f'D64 {d64.name}: {block_count} PRG blocks, chain verified')
 if a.content:
  from scene_format import decode
  files={}
  for name in [f'SCENE{i:02d}' for i in range(1,30)]+['TITLE']:
   data=(a.content/(name+'.bin')).read_bytes();decode(data);files[name]=data
  for name in ['SPEECH','MUSIC','MUSICG','EFFECTS']+[f'ISL{i:02d}' for i in range(1,29)]:
   files[name]=(a.content/(name+'.bin')).read_bytes()
  make_image(output,a.full_d64,files=files)
  print(f'Full D64: {a.full_d64} ({len(files)} content files)')
 table=(ROOT/'dist/symbols.txt').read_text()
 code_end=symbol(table,'cpu_count');last_data=symbol(table,'checksum_sum')+1
 if not (0x1000 < code_end < last_data < 0x3200):raise SystemExit('FATAL: program code/state overlaps the original-art sprite RAM at $3200')
 if symbol(table,'effects_code_end')>0x0c40 or symbol(table,'sample_code_end')>0x0e80 or symbol(table,'intro_poll_end')>0x1000:raise SystemExit('FATAL: music driver overlaps game code')
 if symbol(table,'intro_overlay_end')>0x52f8:raise SystemExit('FATAL: intro overlay overlaps fixed-logo screen cells')
 if symbol(table,'mu_data_end')>0x3400 or symbol(table,'control_data_end')>0x3700:raise SystemExit('FATAL: streaming control data overlaps sprite RAM')
 if symbol(table,'smp_end')>0xC000:raise SystemExit('FATAL: engine/sample bank runs into the $C000 save buffer')
 prg=output.read_bytes();top=prg[0]+256*prg[1]+len(prg)-3
 if top>=0xC000:raise SystemExit(f'FATAL: program ends at ${top:04X}, overlaps the $C000 save buffer')
 print(f'PRG ${prg[0]+256*prg[1]:04X}-${top:04X}, {len(prg)} bytes; free below save buffer: {0xC000-top-1} bytes')
 if a.test:run_tests()
 if a.preview:subprocess.run([sys.executable,str(ROOT/'tools/render_preview.py')],cwd=ROOT,check=True)
 sha=hashlib.sha256(prg).hexdigest()
 d64sha=hashlib.sha256(d64.read_bytes()).hexdigest()
 (ROOT/'dist/SHA256SUMS.txt').write_text(f'{sha}  MegaLoMania64.prg\n{d64sha}  MegaLoMania64.d64\n')
 print(f'SHA256 {sha}  {output.name}')
 if a.package:
  import package
  package.main()
if __name__=='__main__':main()
