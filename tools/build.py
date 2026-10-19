#!/usr/bin/env python3
"""Deterministic assembler-only build; does not require Pillow or an external assembler."""
from pathlib import Path
import argparse,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]

def run_tests():
 result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (ROOT/'dist/build_test_log.txt').write_text(result.stdout)
 print(result.stdout,end='')
 if result.returncode:raise SystemExit(f'Tests failed: {result.returncode}')

def main():
 p=argparse.ArgumentParser(description='Build Island Wars v3.0 native C64C campaign')
 p.add_argument('--test',action='store_true',help='run emulator-based 6502 logic tests')
 p.add_argument('--regen-gfx',action='store_true',help='rebuild asset bin files; requires Pillow')
 p.add_argument('--preview',action='store_true',help='generate PNG VIC-II memory preview; requires Pillow')
 a=p.parse_args()
 if a.regen_gfx:subprocess.run([sys.executable,str(ROOT/'tools/make_gfx.py')],cwd=ROOT,check=True)
 for name,expected in (('charset.bin',2048),('cursor_sprite.bin',64)):
  f=ROOT/'assets'/name
  if not f.is_file() or f.stat().st_size!=expected:raise SystemExit(f'Asset missing/invalid: {f}')
 output=ROOT/'dist/MegaLoMania64.prg'
 subprocess.run([sys.executable,str(ROOT/'tools/asm6502.py'),str(ROOT/'src/main.asm'),'-o',str(output),'--symbols',str(ROOT/'dist/symbols.txt')],cwd=ROOT,check=True)
 from make_d64 import make_image
 d64=ROOT/'dist/MegaLoMania64.d64'
 block_count=make_image(output,d64)
 print(f'D64 {d64.name}: {block_count} PRG blocks, chain verified')
 code_end=int(next(row.split()[0] for row in (ROOT/'dist/symbols.txt').read_text().splitlines() if row.split()[1]=='cpu_count'),16)
 last_data=int(next(row.split()[0] for row in (ROOT/'dist/symbols.txt').read_text().splitlines() if row.split()[1]=='checksum_sum'),16)+1
 if not (0x1000 < code_end < last_data < 0x3700):raise SystemExit('FATAL: program code/state overlaps reserved sprite RAM')
 if a.test:run_tests()
 if a.preview:subprocess.run([sys.executable,str(ROOT/'tools/render_preview.py')],cwd=ROOT,check=True)
 sha=hashlib.sha256(output.read_bytes()).hexdigest()
 d64sha=hashlib.sha256(d64.read_bytes()).hexdigest()
 (ROOT/'dist/SHA256SUMS.txt').write_text(f'{sha}  MegaLoMania64.prg\n{d64sha}  MegaLoMania64.d64\n')
 print(f'SHA256 {sha}  {output.name}')
if __name__=='__main__':main()
