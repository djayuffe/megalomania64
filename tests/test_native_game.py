"""Synthetic end-to-end economic/army/campaign policy checks; no owner content."""
import ctypes,shutil,subprocess,tempfile
from pathlib import Path
import unittest
import test_gameplay_core as core_tests
ROOT=core_tests.ROOT


class NativeGameTest(unittest.TestCase):
    write=core_tests.GameplayCoreTest.write
    word=core_tests.GameplayCoreTest.word
    dword=core_tests.GameplayCoreTest.dword
    read=core_tests.GameplayCoreTest.read
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which('clang')or shutil.which('cc')
        if not compiler:raise __import__('unittest').SkipTest('C compiler unavailable')
        cls.temporary=tempfile.TemporaryDirectory();folder=Path(cls.temporary.name)
        header=folder/'memory.h';header.write_text('#include <stdint.h>\nextern uint8_t world_memory[10496];\n')
        stub=folder/'memory.c';stub.write_text('#include <stdint.h>\nuint8_t world_memory[10496];\n')
        library=folder/'game.so'
        subprocess.run([compiler,'-std=c99','-Wall','-Wextra','-Werror','-shared','-fPIC','-DWORLD_ADDRESS=world_memory','-include',str(header),*[str(ROOT/f'src/gameplay/{name}.c')for name in ['core','world','game']],str(stub),'-o',str(library)],check=True,capture_output=True)
        cls.lib=ctypes.CDLL(str(library))

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def setUp(self):
        core_tests.GameplayCoreTest.setUp(self);self.lib.ng_new()
        self.state=(ctypes.c_uint8*128).in_dll(self.lib,'ng_state')
        self.terrain=(ctypes.c_uint8*16).in_dll(self.lib,'ng_terrain');self.terrain[:]=bytes(16)
        (ctypes.c_uint8*10).in_dll(self.lib,'gp_combat_rules')[:]=bytes([25,0,75,0,25,0,75,0,100,0])
        ctypes.c_uint8.in_dll(self.lib,'world_first').value=0
        ctypes.c_uint8.in_dll(self.lib,'world_last').value=3
        self.word(0xbe,65535);self.word(0xd2,65535);self.word(0x3fe,0)
        self.word(0x2fc,1);self.s[0x446]=1;self.s[0x448]=128
        self.word(0x3d6,100);self.word(0x404,100);self.word(0x406,100)

    def save_sector(self,index):
        ctypes.c_uint8.in_dll(self.lib,'world_slot').value=index;self.terrain[index]=1;self.lib.ng_cache()

    def load_sector(self,index):
        ctypes.c_uint8.in_dll(self.lib,'world_slot').value=index;self.lib.world_get()

    def test_tower_can_be_destroyed_and_captured_through_live_ticks(self):
        self.save_sector(0)
        self.s[:]=bytes(0x449);self.s[0x3b8:0x3c2]=bytes([255])*10;self.word(0x3fe,1);self.word(0x2fc,1);self.word(0x3d6,10)
        self.s[0x446]=1;self.s[0x448]=128;self.word(0xbe,65535);self.word(0xd2,65535)
        army=self.buffers['army'];army[0]=20;self.lib.ng_rule(20,0,0,0);self.save_sector(1)
        self.state[23]=1  # hotseat: isolate combat from AI policy
        for _ in range(10):self.lib.ng_step(100)
        self.assertEqual(self.read(0x3fe),4);self.assertFalse(self.s[0x446]&1)
        for _ in range(30):self.lib.ng_step(100)
        self.assertEqual(self.read(0x3fe),0);self.assertTrue(self.s[0x446]&1)
        self.assertGreater(self.read(0x404),0)

    def test_ai_researches_equips_attacks_and_defeats_an_idle_enemy(self):
        self.save_sector(0)
        self.word(0x3fe,1);self.word(0x174,2000);self.save_sector(1)
        for _ in range(400):
            for slot in [0,1]:self.load_sector(slot);self.lib.ng_step(30)
            self.lib.ng_outcome()
            if self.state[15]!=0:break
        self.assertEqual(self.state[15],2,'AI failed to defeat an idle human tower')
        self.load_sector(1);self.assertTrue(self.read(0x126)&1,'AI did not research an attack design')

    def test_army_move_and_return_conserve_units_and_block_nonadjacent_water(self):
        self.buffers['army'][10]=10;self.lib.ng_rule(20,0,0,0);self.save_sector(0)
        self.s[:]=bytes(0x449);self.s[0x3b8:0x3c2]=bytes([255])*10;self.word(0x3fe,4);self.s[0x448]=128;self.save_sector(1)
        self.assertEqual(self.lib.ng_move(0,2,0),0)
        self.assertEqual(self.lib.ng_move(0,1,0),1)
        self.load_sector(0);self.assertEqual(self.read(0x2f4),0)
        self.load_sector(1);self.assertEqual(self.read(0x2f4),10)
        self.assertEqual(self.lib.ng_move(1,0,0),1)
        self.load_sector(0);self.assertEqual(self.read(0x2f4),10)

    def test_diplomacy_expires_and_attack_breaks_symmetric_alliance(self):
        presence=(ctypes.c_uint16*4).in_dll(self.lib,'ng_presence');presence[:]=[200,100,0,0]
        self.lib.ng_negotiate(1);self.assertEqual(self.buffers['alliances'][:2],[3,3])
        self.lib.ng_clock(599);self.assertEqual(self.buffers['alliances'][:2],[3,3])
        self.lib.ng_clock(1);self.assertEqual(self.buffers['alliances'][:2],[1,2])
        self.lib.ng_negotiate(1);self.lib.ng_break(1);self.assertEqual(self.buffers['alliances'][:2],[1,2])

    def test_victory_defeat_final_completion_and_allied_survival(self):
        self.save_sector(0);self.lib.ng_outcome();self.assertEqual(self.state[15],1)
        self.state[15]=0;self.state[12]=27;self.lib.ng_outcome();self.assertEqual(self.state[15],3)
        self.state[15]=0;self.word(0x3fe,1);self.save_sector(0);self.lib.ng_outcome();self.assertEqual(self.state[15],2)

    def test_nuclear_launch_pays_inventory_and_interceptor_prevents_destruction(self):
        ctypes.c_uint8.in_dll(self.lib,'world_first').value=6
        ctypes.c_uint8.in_dll(self.lib,'world_last').value=9
        self.word(0x126,256);self.word(0x11e,1);self.save_sector(0)
        self.s[:]=bytes(0x449);self.s[0x3b8:0x3c2]=bytes([255])*10;self.word(0x3fe,1);self.s[0x448]=128;self.s[0x446]=1;self.word(0x2fc,1);self.word(0x3d6,100)
        self.s[0x3b8:0x3c2]=bytes([255])*10;self.lib.ng_rule(22,0,0,9);self.save_sector(1)
        self.assertEqual(self.lib.ng_launch(0,1,0,0),1)
        self.load_sector(0);self.assertEqual(self.read(0x11e),0)
        self.load_sector(1);self.assertGreater(self.s[0x444],60)
        self.state[23]=1
        self.lib.ng_step(200)
        self.assertFalse(self.s[0x448]&64);self.assertEqual(self.s[0x444],0)
        self.assertEqual(self.s[0x3b8],255)

    def test_unintercepted_nuclear_hit_removes_armies_and_land(self):
        self.s[0x444]=20;self.word(0x43e,1);self.state[23]=1
        self.buffers['army'][0]=2;self.lib.ng_rule(20,0,0,0)
        self.lib.ng_step(30)
        self.assertTrue(self.s[0x448]&64);self.assertFalse(self.s[0x448]&128)
        self.assertEqual(self.read(0x2f4),0);self.assertEqual(self.s[0x446]&15,0)

    def test_hotseat_elimination_keeps_other_factions_playing(self):
        self.state[23]=1;self.state[14]=15
        self.word(0x3fe,1);self.save_sector(0)
        self.word(0x3fe,2);self.save_sector(1)
        self.lib.ng_outcome()
        self.assertEqual(self.state[13],1)
        self.assertEqual(self.state[15],0)
        self.load_sector(1);self.s[0x448]|=64;self.lib.ng_cache();self.lib.ng_outcome()
        self.assertEqual(self.state[15],1)

    def test_nuclear_defence_retaliates_against_original_source(self):
        ctypes.c_uint8.in_dll(self.lib,'world_first').value=6
        ctypes.c_uint8.in_dll(self.lib,'world_last').value=9
        self.word(0x126,256);self.word(0x11e,1);self.save_sector(0)
        self.word(0x3fe,1);self.word(0x126,0);self.word(0x11e,0)
        self.lib.ng_rule(22,0,0,8);self.save_sector(1)
        self.assertEqual(self.lib.ng_launch(0,1,0,0),1)
        self.state[23]=1;self.load_sector(1)
        self.lib.ng_step(70)
        self.assertEqual(self.s[0x3b8],255)
        self.load_sector(0)
        self.assertGreater(self.s[0x444],0)
        self.assertEqual(self.read(0x43e),1)
        self.assertEqual(self.read(0x440),255)

    def test_air_transfer_crosses_water_and_leaves_ground_army_at_source(self):
        ctypes.c_uint8.in_dll(self.lib,'world_first').value=6
        ctypes.c_uint8.in_dll(self.lib,'world_last').value=9
        army=self.buffers['army'];army[6]=10;army[10]=5
        self.lib.ng_rule(20,0,0,0);self.save_sector(0)
        self.s[:]=bytes(0x449);self.s[0x3b8:0x3c2]=bytes([255])*10
        self.word(0x3fe,4);self.s[0x448]=128;self.save_sector(15)
        self.assertEqual(self.lib.ng_move(0,15,0),1)
        self.load_sector(0);self.assertEqual(self.s[0x2c8+10],5);self.assertEqual(self.s[0x2c8+6],0)
        self.load_sector(15);self.assertEqual(self.s[0x2c8+6],10);self.assertEqual(self.s[0x2c8+10],0)

    def test_hotseat_truce_expires_for_its_original_participants(self):
        presence=(ctypes.c_uint16*4).in_dll(self.lib,'ng_presence');presence[:]=[200,100,150,50]
        self.lib.ng_negotiate(1)
        self.state[13]=2;self.lib.ng_negotiate(3)
        self.lib.ng_clock(600)
        self.assertEqual(self.buffers['alliances'][:],[1,2,4,8])
