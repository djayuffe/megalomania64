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
                           ('research_points', 12), ('technology_points', 20),
                           ('army', 11), ('army_rules', 66), ('defence_rules', 60),
                           ('alliances', 4)]:
            array = (ctypes.c_uint8 * size).in_dll(self.lib, 'gp_' + name)
            array[:] = bytes(size)
            self.buffers[name] = array
        self.s = self.buffers['sector']
        self.buffers['recipe'][:] = bytes([255, 0] * 5)
        self.buffers['classes'][:] = bytes([0] * 4 + [1] * 4 + [2] * 12)
        self.buffers['alliances'][:] = bytes([1, 2, 4, 8])
        for age in range(11):
            self.write('army_rules', age * 2, 10 + age)
            self.write('army_rules', 22 + age * 2, 1 + age)
            self.write('army_rules', 44 + age * 2, 2 if age == 4 else 1)
        for age in range(10):
            self.write('defence_rules', age * 2, 20 + age)
            self.write('defence_rules', 20 + age * 2, 2 + age)
            self.write('defence_rules', 40 + age * 2, 0 if age >= 8 else 1)
        for building, (turrets, offset) in enumerate([(4, 0x3b8), (2, 0x3bc), (1, 0x3be), (3, 0x3bf)]):
            self.write('buildings', building * 24 + 20, turrets)
            self.write('buildings', building * 24 + 22, offset)
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

    def run_rule(self, op, a=0, b=0, c=0, run=0, seed=0, active=15):
        self.buffers['request'][:] = bytes(32)
        self.buffers['request'][0] = op
        for at, value in [(2, a), (4, b), (6, c), (8, run), (10, seed), (28, 9), (30, active)]:
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

    def test_army_men_include_weapon_crews(self):
        self.buffers['army'][4] = 3
        self.buffers['army'][10] = 5
        self.assertEqual(self.run_rule(18), 11)

    def test_arrival_fills_capacity_with_high_age_units_first(self):
        self.s[0x2c8] = 240
        self.word(0x2f4, 240)
        for age, count in [(9, 3), (4, 10), (0, 20), (10, 10)]:
            self.buffers['army'][age] = count
        self.assertEqual(self.run_rule(20, a=0), 33)
        self.assertEqual(self.read(0x2f4), 250)
        self.assertEqual(self.s[0x2c8 + 9], 3)
        self.assertEqual(self.s[0x2c8 + 4], 7)
        self.assertEqual(self.buffers['army'][4], 3)
        self.assertEqual(self.buffers['army'][0], 20)

    def test_reinforcing_a_type_preserves_its_damaged_front_unit(self):
        self.s[0x2c8] = 1
        self.word(0x2f4, 1)
        self.word(0x308, 3)
        self.buffers['army'][0] = 2
        self.run_rule(20, a=0)
        self.assertEqual(self.read(0x308), 3)
        self.assertEqual(self.s[0x2c8], 3)

    def test_army_casualty_updates_unit_and_strength_caches(self):
        self.s[0x2c8 + 4] = 2
        self.word(0x2f4, 2)
        self.word(0x3f4, 10)
        self.word(0x368, 10)
        self.run_rule(19, b=0, c=4)
        self.assertEqual(self.s[0x2c8 + 4], 1)
        self.assertEqual(self.read(0x2f4), 1)
        self.assertEqual(self.read(0x3f4), 5)
        self.assertEqual(self.read(0x368), 5)

    def test_arriving_army_starts_construction_without_capturing_land(self):
        self.word(0x3fe, 4)
        self.word(0xa, 65535)
        self.buffers['army'][10] = 20
        self.run_rule(20, a=1)
        self.assertEqual(self.read(0x3fe), 4)
        self.assertEqual(self.read(0xa), 1)
        self.assertEqual(self.read(0x28), 20)
        self.assertEqual(self.read(0x2a, 4), 48000)

    def test_alliance_stops_neutral_tower_construction(self):
        self.word(0x3fe, 4)
        self.word(0xa, 1)
        self.word(0x2f6, 20)
        self.s[0x2c8 + 11 + 10] = 20
        self.word(0x28, 20)
        self.buffers['alliances'][1] = 3
        self.run_rule(21)
        self.assertEqual(self.read(0xa), 65535)
        self.assertEqual(self.read(0x28), 0)

    def test_enemy_arrival_contests_neutral_construction(self):
        self.word(0x3fe, 4)
        self.word(0xa, 1)
        for faction in [1, 2]:
            self.word(0x2f4 + faction * 2, 10)
            self.s[0x2c8 + faction * 11 + 10] = 10
        self.word(0x28, 10)
        self.run_rule(21)
        self.assertEqual(self.read(0xa), 65535)
        self.assertEqual(self.read(0x28), 0)

    def test_damage_skips_allies_and_returns_unspent_damage(self):
        self.buffers['alliances'][0] = 3
        for faction in [1, 2]:
            self.s[0x2c8 + faction * 11] = 1
            self.word(0x2f4 + faction * 2, 1)
            self.word(0x308 + faction * 22, 10)
            self.word(0x360 + faction * 22, 1)
            self.word(0x3f4 + faction * 2, 1)
        self.assertEqual(self.run_rule(24, a=15, b=0), 5)
        self.assertEqual(self.read(0x2f6), 1)
        self.assertEqual(self.read(0x2f8), 0)

    def test_allied_turret_damage_preserves_original_predicate_return(self):
        self.word(0x3fe, 0)
        before = bytes(self.s)
        self.assertEqual(self.run_rule(25, a=30, b=0, seed=123), 1)
        self.assertEqual(bytes(self.s), before)
        self.assertEqual(bytes(self.buffers['request'][10:12]), bytes([123, 0]))

    def test_destroying_a_turret_removes_crew_and_strength(self):
        self.s[0x3b8:0x3c2] = bytes([255] * 10)
        self.word(0x3fe, 0)
        self.word(0x404, 100)
        self.run_rule(22, a=0, b=0, c=0)
        self.assertEqual(self.read(0x3f4), 2)
        self.assertEqual(self.run_rule(25, a=20, b=1), 0)
        self.assertEqual(self.s[0x3b8], 255)
        self.assertEqual(self.read(0x404), 99)
        self.assertEqual(self.read(0x3f4), 0)
        self.assertEqual(self.read(0x2fe), 0)

    def test_nuclear_arrival_schedules_flight_without_army_units(self):
        self.buffers['army'][8] = 1
        self.run_rule(20, a=2)
        self.assertEqual(self.read(0x43e), 2)
        self.assertTrue(100 <= self.s[0x444] < 140)
        self.assertEqual(self.read(0x2f8), 0)
        self.assertEqual(self.buffers['army'][8], 1)

    def test_gatherable_buffer_selects_fast_slow_and_stopped_rates(self):
        self.word(0x140, 0)
        self.word(0x142, 100)
        for stock, rate in [(120, 775), (121, 126), (140, 126), (141, 0)]:
            self.word(0x174, stock)
            self.run_rule(26)
            self.assertEqual(self.read(0x13e), rate)
            self.assertEqual(self.read(0x136, 4), 2400)

    def test_gathering_converts_raw_material_without_increasing_total_stock(self):
        self.word(0x140, 0)
        self.word(0x142, 100)
        self.word(0x174, 100)
        self.run_rule(26)
        self.run_rule(27, a=4)
        self.assertEqual(self.read(0x142), 99)
        self.assertEqual(self.read(0x174), 100)
        self.word(0x174, 20)
        self.run_rule(26)
        self.assertEqual(self.read(0x142), 20)


if __name__ == '__main__':
    unittest.main()
