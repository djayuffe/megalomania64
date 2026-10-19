"""Build-system tests: reproducibility, generated files, disk image, packaging."""
import hashlib, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
from common import *

class Tools(unittest.TestCase):
    def test_generated_tables_and_sprite_are_up_to_date(self):
        for gen,out in (('tools/gen_tables.py','src/tables.asm'),('tools/make_sprites.py','assets/source_sprite.bin')):
            before=(ROOT/out).read_bytes()
            subprocess.run([sys.executable,str(ROOT/gen)],cwd=ROOT,check=True,capture_output=True)
            self.assertEqual((ROOT/out).read_bytes(),before,f'{out} is stale: run tools/build.py')
    def test_assembly_is_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            outs=[]
            for n in (1,2):
                o=Path(d)/f'{n}.prg'
                subprocess.run([sys.executable,str(ROOT/'tools/asm6502.py'),str(ROOT/'src/main.asm'),'-o',str(o)],check=True,capture_output=True)
                outs.append(hashlib.sha256(o.read_bytes()).hexdigest())
            self.assertEqual(outs[0],outs[1])
            build();self.assertEqual(hashlib.sha256(PRG.read_bytes()).hexdigest(),outs[0])
    def test_basic_stub_and_entry(self):
        build();prg=PRG.read_bytes()
        self.assertEqual(prg[:2],b'\x01\x08')
        self.assertEqual(prg[2:2+12],bytes([0x0B,0x08,0x0A,0x00,0x9E,0x34,0x30,0x39,0x36,0,0,0]))   # 10 SYS4096
        self.assertEqual(symbols()['start'],0x1000)
    def test_music_tables_are_in_sid_range(self):
        build();s=symbols();c=CPU(PRG)
        lo=c.m[s['melody_lo']:s['melody_lo']+96];hi=c.m[s['melody_hi']:s['melody_hi']+96]
        for i in range(64):
            freq=lo[i]+256*hi[i]
            self.assertTrue(500<freq<20000,(i,freq))     # ~30 Hz..~1.2 kHz: audible, nothing degenerate
    def test_package_is_reproducible_and_complete(self):
        sys.path.insert(0,str(ROOT/'tools'))
        import package
        package.main();a=hashlib.sha256((ROOT/'dist'/f'MegaLoMania64_v{(ROOT/"VERSION").read_text().strip()}_Source.zip').read_bytes()).hexdigest()
        package.main();target=ROOT/'dist'/f'MegaLoMania64_v{(ROOT/"VERSION").read_text().strip()}_Source.zip'
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),a)
        names=zipfile.ZipFile(target).namelist()
        for need in ('MegaLoMania64/src/main.asm','MegaLoMania64/src/irq.asm','MegaLoMania64/dist/MegaLoMania64.prg',
                     'MegaLoMania64/dist/MegaLoMania64.d64','MegaLoMania64/tests/test_engine.py','MegaLoMania64/assets/source_sprite.bin'):
            self.assertIn(need,names)
        self.assertFalse([n for n in names if '__pycache__' in n or n.endswith('.pyc')])
if __name__=='__main__':unittest.main()
