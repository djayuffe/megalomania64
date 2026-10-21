"""Native integration contracts, using synthetic sector and disk data only."""
import ctypes
import random
import shutil
import struct
import subprocess
import tempfile
from common import *
from asm6502 import Assembler
from native_world import encode,decode,spans,SLOT,RECORD
from build_native import picture


class NativeHardware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.prg=Path(cls.tmp.name)/'support.prg'
        a=Assembler(ROOT/'src/gameplay/hardware.asm')
        a.sym.update(RUNTIME_MAIN=0x8000,ZP_STACK=2);a.assemble(cls.prg)
        cls.sym=a.sym

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):self.cpu=CPU(self.prg)

    def test_start_zeros_bss_and_keeps_world_and_stack_separate(self):
        c=self.cpu;c.m[0x7000:0x8000]=bytes([0x7e])*4096
        c.m[0x4000:0x6900]=bytes([0x5a])*10496
        c.m[0xc000:0xc400]=bytes([0xa5])*1024
        c.pc=self.sym['runtime_start'];c.run_until(0x8000,max_steps=100000)
        self.assertEqual(c.m[0x7000:0x8000],bytes(4096))
        self.assertEqual(c.m[0x4000:0x6900],bytes([0x5a])*10496)
        self.assertEqual(c.m[2:4],b'\xff\xc3')
        self.assertEqual(c.m[0xc000:0xc400],bytes([0xa5])*1024)
        self.assertLessEqual(self.sym['support_end'],0x2960)
        self.assertLessEqual(self.sym['support_loader_end'],0x1000)
        self.assertEqual(c.m[0xd025],0)

    def test_joystick_directions_and_fire_are_edge_triggered(self):
        c=self.cpu
        for state,key in [(0x1e,87),(0x1d,83),(0x1b,65),(0x17,68),(0x0f,13)]:
            c.joystick=0xff;c.call(self.sym['hw_key']);self.assertEqual(c.a,0)
            c.joystick=state;c.call(self.sym['hw_key']);self.assertEqual(c.a,key)
            c.call(self.sym['hw_key']);self.assertEqual(c.a,0)
        c.key=ord('R');c.call(self.sym['hw_key']);self.assertEqual(c.a,ord('R'))

    def test_sequential_reopen_last_byte_and_truncation(self):
        c=self.cpu;c.drive_files={'FIRST':b'NGR1abc','NEXT':b'NGW2xyz'}
        for name in c.drive_files:
            c.m[0x200:0x200+len(name)+1]=name.encode()+b'\0'
            c.a=0;c.x=2;c.call(self.sym['hw_open']);self.assertEqual(c.a,1)
            actual=[]
            for _ in c.drive_files[name]:
                c.call(self.sym['hw_read']);actual.append(c.a)
                self.assertEqual(c.m[self.sym['hw_error']],0)
            self.assertEqual(bytes(actual),c.drive_files[name])
            c.call(self.sym['hw_read']);self.assertEqual(c.m[self.sym['hw_error']],1)
            c.call(self.sym['hw_close'])
        self.assertEqual(c.m[0xd011]&16,16)
        c.raster_msb=128;c.call(self.sym['hw_close'])
        self.assertEqual(c.m[0xd011]&0x90,0x10)


class NativeWorld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which('clang')or shutil.which('cc')
        if not compiler:raise unittest.SkipTest('C compiler unavailable')
        cls.tmp=tempfile.TemporaryDirectory();folder=Path(cls.tmp.name)
        header=folder/'memory.h';header.write_text('#include <stdint.h>\nextern uint8_t world_memory[10496];\n')
        stub=folder/'memory.c';stub.write_text('#include <stdint.h>\nuint8_t world_memory[10496];\n')
        lib=folder/'world.so'
        subprocess.run([compiler,'-shared','-fPIC','-Wall','-Wextra','-Werror','-DWORLD_ADDRESS=world_memory','-include',str(header),str(ROOT/'src/gameplay/core.c'),str(ROOT/'src/gameplay/world.c'),str(stub),'-o',str(lib)],check=True,capture_output=True)
        cls.lib=ctypes.CDLL(str(lib))

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_c_and_python_match_every_legal_age_window_and_slot(self):
        rng=random.Random(1991)
        memory=(ctypes.c_uint8*(SLOT*16)).in_dll(self.lib,'world_memory')
        sector=(ctypes.c_uint8*RECORD).in_dll(self.lib,'gp_sector')
        for first in range(10):
            for last in range(first,min(10,first+4)):
                ctypes.c_uint8.in_dll(self.lib,'world_first').value=first
                ctypes.c_uint8.in_dll(self.lib,'world_last').value=last
                for slot in range(16):
                    raw=bytearray(rng.randrange(256)for _ in range(RECORD))
                    for k in range(4):
                        at=12+k*24;workers=rng.randrange(251);active=rng.randrange(2)
                        struct.pack_into('<H',raw,at+4,workers)
                        struct.pack_into('<I',raw,at+6,48000 if active else 0xffffffff)
                        struct.pack_into('<H',raw,at+14,workers-workers//32 if active else 0)
                    expected=encode(raw,first,last);sector[:]=raw
                    ctypes.c_uint8.in_dll(self.lib,'world_slot').value=slot
                    self.lib.world_put();self.assertEqual(bytes(memory[slot*SLOT:(slot+1)*SLOT]),expected)
                    self.lib.world_get();self.assertEqual(bytes(sector),decode(expected,first,last))

    def test_rejects_invalid_windows_lengths_and_padding(self):
        for first,last in [(0,4),(3,2),(-1,0),(9,10)]:
            with self.assertRaises(ValueError):spans(first,last)
        for data in [b'',bytes(SLOT-1)]:
            with self.assertRaises(ValueError):decode(data,0,3)
        data=bytearray(SLOT);data[-1]=1
        with self.assertRaises(ValueError):decode(data,0,3)

    def test_picture_is_bounded_and_retains_source_silhouette(self):
        data=b'MLC1'+bytes([5,3,15])+bytes([0x55]*63+[0])*2
        glyphs,inks=picture(data)
        self.assertEqual(glyphs,bytes([255])*96);self.assertEqual(inks,[5]*12)
        with self.assertRaises(ValueError):picture(data[:-1])
