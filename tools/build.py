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
 a=p.parse_args()
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
 table=(ROOT/'dist/symbols.txt').read_text()
 code_end=symbol(table,'cpu_count');last_data=symbol(table,'checksum_sum')+1
 if not (0x1000 < code_end < last_data < 0x3200):raise SystemExit('FATAL: program code/state overlaps the original-art sprite RAM at $3200')
 if symbol(table,'engine_end')>=0x5800:raise SystemExit('FATAL: engine code overlaps the intro picture data at $5800')
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
