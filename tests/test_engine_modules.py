"""Execute production cache/loader functions against a mocked IEC bus.

The host has no C64 address space. Only the hardware and decoder boundary is
mocked; audio(), ng_engine_load(), and the module directory come from runtime.c.
"""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EngineModules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT/'src/gameplay/runtime.c').read_text()
        audio = source[source.index('static void audio('):source.index('\n#ifdef __CC65__', source.index('static void audio('))]
        directory = source[source.index('typedef struct {const char *file,*signature;}'):source.index('\nstatic void ensure_overlay(')]
        harness = r'''
#include <stdint.h>
#include <string.h>
uint8_t loaded_clip=255,loaded_engine=255,runtime_ready,clip_voice;
uint8_t busy,open_ok=1,decode_ok=1,signature_ok=1,owner,plays,opens;
uint16_t payload_size=100;
uint8_t regs[65536];
#define REG(a) regs[a]
void filename(const char *prefix,uint8_t id) {(void)prefix;(void)id;}
char file[8];
uint8_t hw_audio_busy(void) {return busy;}
uint8_t hw_open(const char *name) {(void)name;++opens;return open_ok;}
void hw_close(void) {}
uint8_t signature(const char *s) {(void)s;return signature_ok;}
uint16_t read_word(void) {return payload_size;}
uint8_t hw_read(void) {return 0;}
uint8_t unpack(uint8_t *dest,uint16_t size) {(void)dest;(void)size;++owner;return decode_ok;}
void hw_play(uint16_t size) {(void)size;++plays;}
'''
        cls.tmp = tempfile.TemporaryDirectory()
        path = Path(cls.tmp.name)
        (path/'loader.c').write_text(harness+audio+directory+'\nvoid play_clip(uint8_t id) {audio(id);}\n')
        subprocess.run(['clang','-shared','-fPIC','-Wall','-Wextra','-Werror',str(path/'loader.c'),'-o',str(path/'loader.so')],check=True,capture_output=True)
        cls.lib = ctypes.CDLL(str(path/'loader.so'))
        cls.lib.ng_engine_load.argtypes = [ctypes.c_uint8]
        cls.lib.ng_engine_load.restype = ctypes.c_uint8

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def byte(self, name, value=None):
        item = ctypes.c_uint8.in_dll(self.lib, name)
        if value is not None:
            item.value = value
        return item.value

    def setUp(self):
        for key,value in dict(loaded_clip=255,loaded_engine=255,runtime_ready=0,busy=0,open_ok=1,decode_ok=1,signature_ok=1,owner=0,plays=0,opens=0).items():
            self.byte(key,value)
        ctypes.c_uint16.in_dll(self.lib,'payload_size').value=100

    def test_every_engine_reloads_after_audio_and_audio_reloads_after_engine(self):
        for engine in range(8):
            self.assertEqual(self.lib.ng_engine_load(engine),1)
            self.lib.play_clip(7)
            self.assertEqual(self.byte('loaded_engine'),255)
            before=self.byte('opens')
            self.assertEqual(self.lib.ng_engine_load(engine),1)
            self.assertEqual(self.byte('opens'),before+1)
            self.assertEqual(self.byte('loaded_clip'),255)
            self.lib.play_clip(7)
            self.assertEqual(self.byte('opens'),before+2)

    def test_failed_partial_engine_load_cannot_leave_old_engine_cached(self):
        self.lib.ng_engine_load(0)
        self.byte('decode_ok',0)
        self.assertEqual(self.lib.ng_engine_load(1),0)
        self.assertEqual(self.byte('loaded_engine'),255)
        self.byte('decode_ok',1)
        before=self.byte('opens')
        self.assertEqual(self.lib.ng_engine_load(0),1)
        self.assertEqual(self.byte('opens'),before+1)

    def test_partial_audio_failure_invalidates_engine(self):
        self.lib.ng_engine_load(0)
        self.byte('decode_ok',0)
        self.lib.play_clip(7)
        self.assertEqual(self.byte('loaded_engine'),255)
        self.assertEqual(self.byte('loaded_clip'),255)
        self.assertEqual(self.byte('plays'),0)

    def test_busy_audio_and_invalid_module_do_not_write_overlay(self):
        self.byte('busy',1)
        self.assertEqual(self.lib.ng_engine_load(0),0)
        self.assertEqual(self.lib.ng_engine_load(8),0)
        self.assertEqual(self.byte('opens'),0)
        self.assertEqual(self.byte('owner'),0)

    def test_cached_engine_avoids_disk_access(self):
        self.lib.ng_engine_load(3)
        self.assertEqual(self.lib.ng_engine_load(3),1)
        self.assertEqual(self.byte('opens'),1)
