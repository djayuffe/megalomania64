"""Build-system tests: reproducibility, generated files, disk image, packaging."""
import hashlib, json, subprocess, sys, tempfile, unittest, zipfile
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


class OriginalData(unittest.TestCase):
    """Importer + converted original-art assets (the original files themselves are not in the repo)."""
    def synthetic_ilbm(self):
        import struct
        w,h=20,3
        rows=[[(x+y)%4 for x in range(w)] for y in range(h)]
        stride=4
        raw=bytearray()
        for y in range(h):
            for p in range(2):
                line=bytearray(stride)
                for x in range(w):
                    if rows[y][x]>>p&1:line[x>>3]|=0x80>>(x&7)
                raw+=line
        packed=bytearray()
        for i in range(0,len(raw),3):               # literal runs only ...
            c=raw[i:i+3];packed+=bytes([len(c)-1])+c
        packed+=bytes([257-5,0x7f])                # ... then a repeat run (extra data is ignored)
        bmhd=struct.pack('>HHhhBBBBHBBhh',w,h,0,0,2,0,1,0,0,10,11,w,h)
        cmap=bytes([0,0,0,255,0,0,0,255,0,0,0,255])
        def ck(i,d):return i+struct.pack('>I',len(d))+d+(b'\0' if len(d)&1 else b'')
        body=ck(b'BMHD',bmhd)+ck(b'CMAP',cmap)+ck(b'BODY',bytes(packed))
        return b'FORM'+struct.pack('>I',4+len(body))+b'ILBM'+body,rows
    def test_ilbm_reader_decodes_planar_byterun1(self):
        from orig_import import load_ilbm
        data,rows=self.synthetic_ilbm()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'t.lbm';p.write_bytes(data)
            w,h,pal,got=load_ilbm(p)
        self.assertEqual((w,h),(20,3));self.assertEqual(got,rows);self.assertEqual(pal[1],(255,0,0))
    def test_ilbm_reader_rejects_other_files(self):
        from orig_import import load_ilbm
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_bytes(b'RIFF0000WAVE')
            with self.assertRaises(ValueError):load_ilbm(p)
    def test_converted_assets_are_well_formed(self):
        import json
        a=ROOT/'assets/orig'
        army=(a/'army_frames.bin').read_bytes();bld=(a/'build_icons.bin').read_bytes()
        self.assertEqual((len(army),len(bld)),(2560,640))
        for blob in (army[i:i+64] for i in range(0,2560,64)):self.assertEqual(blob[63],0)
        for blob in (bld[i:i+64] for i in range(0,640,64)):self.assertEqual(blob[63],0)
        t=json.loads((a/'orig_text.json').read_text())
        self.assertEqual(len(t['islands']),26);self.assertEqual((t['islands'][0],t['islands'][-1]),('ALOHA','ZAPPA'))
        self.assertEqual(t['finale'],'MEGALOMANIA')
        from PIL import Image
        g=Image.open(a/'galaxy_c64.png');self.assertEqual(g.size,(160,200))
        px=g.tobytes();self.assertTrue(set(px)<=set(range(16)))
        self.assertFalse(any(px[:160*58]))     # the logo band stays black
    def test_island_names_are_shown_on_the_map_screen(self):
        build();s=symbols();c=CPU(PRG);c.call(s['new_game'])
        names=json.loads((ROOT/'assets/orig/orig_text.json').read_text())['islands']+['MEGALOMANIA','THE MOTHER']
        for stage,name in enumerate(names):
            c.m[s['campaign_island']]=stage;c.call(s['load_island'])
            shown=''.join(chr((v&63)+64) if (v&63)<32 and v&63 else chr(v&127) for v in c.m[0x400+20:0x400+31])
            self.assertEqual(shown.strip(),name,stage)
