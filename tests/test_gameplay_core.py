"""Portable regression checks for the new rules core; no original assets needed.

The original-executable differential suite is tools/verify_gameplay.py.
These tests use deliberately synthetic rule tables and compile only the core.
"""
import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GameplayCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('clang') or shutil.which('cc')
        if not compiler:
            raise unittest.SkipTest('host C compiler unavailable')
        cls.temporary = tempfile.TemporaryDirectory(prefix='mlm-gameplay-')
        library = Path(cls.temporary.name) / 'core.so'
        subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                        '-shared', '-fPIC', '-o', str(library),
                        str(ROOT / 'src/gameplay/core.c')], check=True,
                       capture_output=True)
        cls.lib = ctypes.CDLL(str(library))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.buffers = {}
        for name, size in [('sector', 0x449), ('request', 32), ('recipe', 10),
                           ('classes', 20), ('buildings', 96), ('patterns', 270),
                           ('groups', 20), ('complexity', 14), ('manufacture', 14),
                           ('research_points', 12), ('technology_points', 20)]:
            array = (ctypes.c_uint8 * size).in_dll(self.lib, 'gp_' + name)
            array[:] = bytes(size)
            self.buffers[name] = array
        self.s = self.buffers['sector']
        self.buffers['recipe'][:] = bytes([255, 0] * 5)
        self.buffers['classes'][:] = bytes([0] * 4 + [1] * 4 + [2] * 12)
        for slot in range(4):
            self.word(0x140 + slot * 16, 65535)
        for i in range(7):
            self.write('complexity', i * 2, 10)
            self.write('manufacture', i * 2, 1)
        for i in range(6):
            self.write('research_points', i * 2, 1)
        for i in range(9):
            self.write('technology_points', i * 2, 3)
        # Synthetic one-ingredient designs, unrelated to extracted game data.
        for i in range(30):
            self.buffers['patterns'][i * 9:i * 9 + 3] = bytes([1, 0, 3])
        self.word(0xbe, 65535)
        self.word(0xd2, 65535)

    def write(self, name, offset, value, width=2):
        self.buffers[name][offset:offset + width] = value.to_bytes(width, 'little')

    def word(self, offset, value):
        self.write('sector', offset, value)

    def dword(self, offset, value):
        self.write('sector', offset, value, 4)

    def read(self, offset, width=2):
        return int.from_bytes(bytes(self.s[offset:offset + width]), 'little')

    def run_rule(self, op, a=0, b=0, c=0, run=0):
        self.buffers['request'][:] = bytes(32)
        self.buffers['request'][0] = op
        for at, value in [(2, a), (4, b), (6, c), (8, run), (28, 9)]:
            self.write('request', at, value)
        self.lib.gp_dispatch()
        return int.from_bytes(bytes(self.buffers['request'][12:14]), 'little')

    def test_birth_uses_idle_population_and_stops_at_cap(self):
        self.word(0x404, 997)
        self.run_rule(0, 10)
        self.run_rule(1, 6000)
        self.assertEqual(self.read(0x404), 998)
        self.assertEqual(self.read(0x406), 11)

    def test_large_idle_population_disables_birth_rate(self):
        self.run_rule(0, 499)
        self.assertEqual(self.read(0xbc), 0)
        self.run_rule(0, 498)
        self.assertEqual(self.read(0xbc), 484)

    def test_reallocation_preserves_mining_progress(self):
        self.word(0x406, 50)
        self.word(0x140, 4)
        self.word(0x142, 100)
        self.word(0x134, 10)
        self.dword(0x13a, 1234)
        self.run_rule(2, 20, 0)
        self.assertEqual(self.read(0x406), 40)
        self.assertEqual(self.read(0x13a, 4), 1234)

    def test_deposit_exhaustion_returns_workers_once(self):
        self.word(0x406, 30)
        self.word(0x140, 4)
        self.word(0x142, 1)
        self.run_rule(2, 10, 0)
        self.run_rule(3, 300)
        self.assertEqual(self.read(0x17c), 1)
        self.assertEqual(self.read(0x406), 30)
        self.assertEqual(self.read(0x136, 4), 0xffffffff)
        before = bytes(self.s)
        self.run_rule(3, 300)
        self.assertEqual(bytes(self.s), before)

    def test_resource_payment_is_atomic(self):
        self.buffers['recipe'][:] = bytes([0, 2, 1, 3, 255, 0, 255, 0, 255, 0])
        self.word(0x174, 10)
        self.word(0x176, 2)
        before = bytes(self.s)
        self.assertEqual(self.run_rule(5, 1), 0)
        self.assertEqual(bytes(self.s), before)

    def test_stock_does_not_imply_deposit_access(self):
        self.word(0x140, 8)
        self.word(0x142, 100)
        self.word(0x184, 10)
        self.run_rule(9)
        self.assertEqual(self.s[0x432], 0)
        self.assertEqual(self.s[0x434], 4)
        self.s[0x446] = 2
        self.run_rule(9)
        self.assertEqual(self.s[0x432], 1)

    def test_unaffordable_research_leaves_all_workers_in_place(self):
        self.word(0x406, 80)
        before = bytes(self.s)
        self.run_rule(17, 20, 2, 0)
        self.assertEqual(bytes(self.s), before)

    def test_research_reassignment_preserves_progress_and_recipe(self):
        self.word(0x174, 100)
        self.word(0x406, 100)
        self.run_rule(17, 20, 2, 0)
        self.run_rule(15, 100)
        progress = self.read(0xca, 4)
        recipe = bytes(self.s[0x264:0x26e])
        self.run_rule(17, 30, 2, 0)
        self.assertEqual(self.read(0xca, 4), progress)
        self.assertEqual(bytes(self.s[0x264:0x26e]), recipe)
        self.assertEqual(self.read(0x406), 70)

    def test_research_credit_and_worker_release_happen_once(self):
        self.word(0x174, 100)
        self.word(0x406, 100)
        self.run_rule(17, 20, 2, 0)
        self.run_rule(15, 750)
        self.assertEqual(self.read(0x126), 1)
        self.assertEqual(self.read(0x41a), 1)
        self.assertEqual(self.read(0x406), 100)
        before = bytes(self.s)
        self.run_rule(15, 750)
        self.assertEqual(bytes(self.s), before)

    def test_factory_pays_each_unit_and_releases_workers(self):
        self.word(0x406, 100)
        self.word(0x174, 10)
        self.word(0x126, 1)
        self.word(0x42e, 1)
        self.s[0x264:0x26e] = bytes([0, 2, 255, 0, 255, 0, 255, 0, 255, 0])
        self.run_rule(13, 20, 2, 0, run=2)
        self.run_rule(14, 900)
        self.assertEqual(self.read(0x10e), 2)
        self.assertEqual(self.read(0x174), 6)
        self.assertEqual(self.read(0x406), 100)
        self.assertEqual(self.read(0xd2), 65535)

    def test_nuclear_age_uses_future_flag(self):
        self.word(0x418, 8)
        self.run_rule(16)
        self.assertEqual(self.read(0x418), 8)
        self.assertEqual(self.s[0x448] & 16, 16)


if __name__ == '__main__':
    unittest.main()
