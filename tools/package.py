#!/usr/bin/env python3
"""Write a reproducible release ZIP (fixed timestamps, sorted entries) with SHA-256 sums."""
from pathlib import Path
import hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
INCLUDE=['README.md','README_NO.md','CHANGELOG.md','VERSION','Makefile','.gitignore','.github',
         'src','assets','tools','tests','docs']
DIST=['MegaLoMania64.prg','MegaLoMania64.d64','SHA256SUMS.txt','symbols.txt','build_test_log.txt','validation_v5.json',
      'preview_title.png','preview_initial.png','preview_truce.png','preview_expansion.png','preview_future.png']
def files():
    out=[]
    for name in INCLUDE:
        p=ROOT/name
        if p.is_dir():out+=[f for f in sorted(p.rglob('*')) if f.is_file() and '__pycache__' not in f.parts]
        elif p.is_file():out.append(p)
    out+=[ROOT/'dist'/n for n in DIST if (ROOT/'dist'/n).is_file()]
    return out
def main():
    version=(ROOT/'VERSION').read_text().strip()
    target=ROOT/'dist'/f'MegaLoMania64_v{version}_Source.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in files():
            info=zipfile.ZipInfo(f'MegaLoMania64/{f.relative_to(ROOT).as_posix()}',(2026,10,19,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,f.read_bytes())
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    (ROOT/'dist'/f'{target.name}.sha256').write_text(f'{digest}  {target.name}\n')
    print(f'{target.name}: {target.stat().st_size} bytes, sha256 {digest}')
if __name__=='__main__':main()
