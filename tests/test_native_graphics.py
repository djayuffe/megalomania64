"""Bounded original planar conversion with synthetic graphics only."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_graphics import planar_tile,convert,GLYPHS

class TerrainGraphics(unittest.TestCase):
    def test_planar_words_and_source_stride(self):
        data=bytes.fromhex('8000400020001000')+bytes(8)+bytes.fromhex('0001000200040008')+bytes(8)
        pixels=planar_tile(data,0,16,2,16)
        self.assertEqual(pixels[0][:5],[1,2,4,8,0])
        self.assertEqual(pixels[1][-4:],[8,4,2,1])
        with self.assertRaises(ValueError):planar_tile(data,1,16,3,16)

    def test_per_island_characters_keep_text_and_portrait(self):
        tile=[[1 if x==y else 0 for x in range(22)]for y in range(22)]
        font=bytes((i*3)&255 for i in range(2048));portrait=bytes([0xa5])*96
        graphics,mapping,inks,used=convert([tile],[1]*16,[(0,0,0),(255,255,255)],font,portrait)
        self.assertEqual(graphics[32*8:96*8],font[32*8:96*8])
        self.assertEqual(graphics[1024:1120],portrait)
        self.assertEqual(len(mapping),144);self.assertEqual(len(inks),144)
        self.assertTrue(set(mapping)<=set(GLYPHS));self.assertLessEqual(used,144)
        self.assertEqual(mapping[:9],mapping[9:18])
