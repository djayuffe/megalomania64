"""Dialogue routing and private-art conversion contracts."""
import ctypes
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from dialogue_assets import face, descriptors

class Dialogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();path=Path(cls.tmp.name)
        source=(ROOT/'src/gameplay/presentation.c').read_text()
        # Substitute only C64 memory/I/O; run the complete production overlay.
        source=source.replace('#define REG(a) (*(volatile uint8_t *)(a))','#define REG(a) regs[a]')
        harness='''
#include <stdint.h>
#include <string.h>
#define __fastcall__
uint8_t ng_state[128],regs[65536],hw_error;
uint8_t read_index,opened,decoded;
uint8_t hw_open(const char *name) {
    read_index=0;++opened;return !strncmp(name,"NFAC0",5) && name[5]=='0'+ng_state[115];
}
uint8_t hw_read(void) {static const uint8_t h[4]={'N','G','H','1'};uint8_t i=read_index++;return i<4?h[i]:(i-4)%16;}
void hw_close(void) {}
uint8_t unpack(uint8_t *dest,uint16_t size) {
    uint16_t i;++decoded;
    if((uintptr_t)dest!=0x3f80 || size!=128)return 0;
    for(i=0;i<size;++i)regs[0x3f80+i]=(uint8_t)(i+ng_state[115]);
    return 1;
}
void text(uint16_t at,const char *s,uint8_t ink) {while(*s) {regs[0x400+at]=*s++;regs[0xd800+at++]=ink;}}
'''
        (path/'route.c').write_text(harness+source)
        subprocess.run(['clang','-shared','-fPIC','-Wall','-Wextra','-Werror','-I',str(ROOT/'src/gameplay'),str(path/'route.c'),'-o',str(path/'route.so')],check=True,capture_output=True)
        cls.lib=ctypes.CDLL(str(path/'route.so'))
        cls.lib.ng_dialogue_voice.restype=ctypes.c_uint8
        cls.state=(ctypes.c_uint8*128).in_dll(cls.lib,'ng_state')
        cls.regs=(ctypes.c_uint8*65536).in_dll(cls.lib,'regs')

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_all_four_speakers_have_distinct_offer_accept_refuse_streams(self):
        found=[]
        for speaker,base in enumerate([8,22,79,15]):
            for kind in range(3):
                self.state[114]=base+kind;self.state[115]=speaker
                before=bytes(self.state)
                self.assertEqual(self.lib.ng_dialogue_voice(),20+speaker*3+kind)
                self.assertEqual(bytes(self.state),before)
                found.append(self.lib.ng_dialogue_voice())
        self.assertEqual(len(set(found)),12)

    def test_invalid_speaker_and_mismatched_dialogue_do_not_play_other_characters(self):
        for speaker,dialogue in [(4,8),(255,8),(0,22),(1,8),(2,82),(3,14),(3,18)]:
            self.state[114]=dialogue;self.state[115]=speaker
            self.assertEqual(self.lib.ng_dialogue_voice(),255)

    def test_portraits_draw_clean_panel_cache_by_speaker_and_restore_after_invalidation(self):
        self.regs[1]=0x34
        for speaker in range(4):
            self.state[115]=speaker
            ctypes.c_uint8.in_dll(self.lib,'ng_face_owner').value=255
            self.lib.ng_dialogue_draw()
            self.assertEqual(bytes(self.regs[0x3f80:0x4000]),bytes((i+speaker)%256 for i in range(128)))
            for row in range(4):
                at=0x400+425+row*40
                self.assertEqual(bytes(self.regs[at:at+4]),bytes(range(240+row*4,244+row*4)))
                self.assertEqual(bytes(self.regs[0xd800+425+row*40:0xd800+429+row*40]),bytes(range(row*4,row*4+4)))
                self.assertEqual(bytes(self.regs[at+4:at+15]),b' '*11)
            before=ctypes.c_uint8.in_dll(self.lib,'opened').value
            self.lib.ng_dialogue_draw()
            self.assertEqual(ctypes.c_uint8.in_dll(self.lib,'opened').value,before)
            ctypes.c_uint8.in_dll(self.lib,'ng_face_owner').value=255
            self.lib.ng_dialogue_draw()
            self.assertEqual(ctypes.c_uint8.in_dll(self.lib,'opened').value,before+1)
            self.assertEqual(self.regs[1],0x34)

    def test_hires_face_preserves_all_sixteen_cells_and_inks(self):
        # A white planar tile: plane zero set, other colour planes clear.
        raw=(b'\xff\xff'+b'\0'*6)*8
        portrait=face(raw,(0xaf84,0,0,0,8,8,8,2),[(0,0,0),(255,255,255)])
        self.assertEqual(len(portrait),144)
        self.assertEqual(portrait[:128],b'\xff'*128)
        self.assertEqual(portrait[128:],b'\1'*16)

    def test_descriptor_table_uses_original_voice_ids_and_portrait_dimensions(self):
        exe=bytearray(0x34000);ds=0x22f00
        for speaker,base in enumerate([8,22,79,15]):
            pointer=0xcb00+speaker*16
            struct.pack_into('<H',exe,ds+0x2db8+speaker*2,pointer)
            struct.pack_into('<8H',exe,ds+pointer,0xaf84,50400+speaker*24,0xaf86,0,48,55,160,40)
            for kind in range(3):
                at=0xb000+speaker*30+kind*10
                struct.pack_into('<H',exe,ds+0xad74+(base+kind)*2,at)
                word=f'F{speaker}K{kind}'.encode();exe[ds+at:ds+at+len(word)]=word
        rows=descriptors(exe)
        self.assertEqual([r[1] for r in rows],[[f'F{s}K{k}' for k in range(3)] for s in range(4)])
        exe[ds+0xcb00]=0
        with self.assertRaises(ValueError):descriptors(exe)
