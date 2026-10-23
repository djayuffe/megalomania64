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
        subprocess.run([compiler,'-std=c99','-Wall','-Wextra','-Werror','-shared','-fPIC','-DWORLD_ADDRESS=world_memory','-include',str(header),*[str(ROOT/f'src/gameplay/{name}.c')for name in ['core','ai','tactics','military','strategy','world','game','campaign']],str(stub),'-o',str(library)],check=True,capture_output=True)
        cls.lib=ctypes.CDLL(str(library))

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def setUp(self):
        core_tests.GameplayCoreTest.setUp(self);self.lib.ng_new()
        self.state=(ctypes.c_uint8*128).in_dll(self.lib,'ng_state');self.state[126]=0
        self.terrain=(ctypes.c_uint8*16).in_dll(self.lib,'ng_terrain');self.terrain[:]=bytes(16)
        (ctypes.c_uint8*10).in_dll(self.lib,'gp_combat_rules')[:]=bytes([25,0,75,0,25,0,75,0,100,0])
        ctypes.c_uint8.in_dll(self.lib,'world_first').value=0
        ctypes.c_uint8.in_dll(self.lib,'world_last').value=3
        ctypes.c_uint8.in_dll(self.lib,'world_factions').value=4
        ctypes.c_uint16.in_dll(self.lib,'world_enemy_men').value=15
        (ctypes.c_uint8*96).in_dll(self.lib,'world_orders')[:]=bytes([0,1,2,3])*24
        personas=(ctypes.c_uint8*224).in_dll(self.lib,'world_personalities');personas[:]=bytes(224)
        for row in range(4):
            for at,n in [(2,24),(4,24),(6,24),(8,28),(0x18,100),(0x1a,125),(0x1c,150),(0x1e,20),(0x20,30)]:personas[row*56+at]=n
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
        self.load_sector(1);self.assertTrue(self.read(0x126),'AI did not research an attack design')

    def test_army_move_and_return_conserve_units_and_block_nonadjacent_water(self):
        self.buffers['army'][10]=10;self.lib.ng_rule(20,0,0,0);self.save_sector(0)
        self.s[:]=bytes(0x449);self.s[0x3b8:0x3c2]=bytes([255])*10;self.word(0x3fe,4);self.s[0x448]=128;self.save_sector(1)
        self.assertEqual(self.lib.ng_move(0,2,0),0)
        self.assertEqual(self.lib.ng_move(0,1,0),1)
        self.load_sector(0);self.assertEqual(self.read(0x2f4),0)
        self.load_sector(1);self.assertEqual(self.read(0x2f4),10)
        self.assertEqual(self.lib.ng_move(1,0,0),1)
        self.load_sector(0);self.assertEqual(self.read(0x2f4),10)

    def test_retreat_losses_apply_at_hostile_origin(self):
        self.buffers['army'][10]=100;self.lib.ng_rule(20,0,0,0)
        self.word(0x3fe,1);self.save_sector(0)
        self.s[:]=bytes(0x449);self.word(0x3fe,0);self.s[0x448]=128;self.save_sector(1)
        self.assertEqual(self.lib.ng_move(0,1,0),1)
        self.load_sector(1);self.assertGreaterEqual(self.read(0x2f4),50);self.assertLessEqual(self.read(0x2f4),90)

    def test_retreat_from_allied_tower_has_no_losses_during_combat(self):
        self.buffers['alliances'][:]=[3,3,4,8]
        self.buffers['army'][10]=100;self.lib.ng_rule(20,0,0,0)
        self.buffers['army'][0]=5;self.lib.ng_rule(20,2,0,0);self.word(0x3fe,1);self.save_sector(0)
        self.s[:]=bytes(0x449);self.word(0x3fe,0);self.s[0x448]=128;self.save_sector(1)
        self.assertEqual(self.lib.ng_move(0,1,0),1)
        self.load_sector(1);self.assertEqual(self.read(0x2f4),100)

    def test_diplomacy_persists_until_departure(self):
        presence=(ctypes.c_uint16*4).in_dll(self.lib,'ng_presence');presence[:]=[200,100,0,0]
        self.lib.ng_negotiate(1);self.assertEqual(self.buffers['alliances'][:2],[3,3])
        self.lib.ng_clock(599);self.assertEqual(self.buffers['alliances'][:2],[3,3])
        self.lib.ng_clock(1);self.assertEqual(self.buffers['alliances'][:2],[3,3])
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

    def test_hotseat_alliance_groups_merge_and_depart_as_groups(self):
        presence=(ctypes.c_uint16*4).in_dll(self.lib,'ng_presence');presence[:]=[200,100,150,50]
        self.lib.ng_negotiate(1)
        self.state[13]=2;self.lib.ng_negotiate(3)
        self.lib.ng_negotiate(1)
        self.assertEqual(self.buffers['alliances'][:],[15,15,15,15])
        self.lib.ng_break(0)
        self.assertEqual(self.buffers['alliances'][:],[11,11,4,11])

    def test_campaign_pool_choice_epoch_and_saved_people_final(self):
        self.state[126]=1;self.terrain[0]=1
        self.assertEqual(self.lib.ng_campaign_action(13),1)
        self.assertEqual(self.state[116],80)
        self.assertEqual(self.state[126],0)
        for island in [0,1,2]:
            self.state[12]=island;self.state[15]=1
            self.assertEqual(self.lib.ng_campaign_action(ord('N')),1)
            if island<2:self.lib.ng_campaign_action(13)
        self.assertEqual(self.state[12],3)
        self.assertEqual(self.state[116],140)
        self.state[12]=26;self.state[15]=1;self.state[34+3]|=3
        self.state[42]=244;self.state[43]=1
        self.lib.ng_campaign_action(ord('N'))
        self.assertEqual(self.state[12],27)
        self.assertEqual(self.state[116],50)

    def test_campaign_spawn_has_chosen_start_and_exact_deployed_population(self):
        self.word(0x3fe,4);self.s[0x446]=0
        self.save_sector(0);self.save_sector(1);self.save_sector(4);self.save_sector(5)
        self.state[127]=4;self.state[126]=0;self.state[118]=30
        self.lib.ng_prepare_island()
        owners=(ctypes.c_uint8*16).in_dll(self.lib,'ng_owners')
        self.assertEqual(owners[4],0)
        self.assertEqual(sorted(owners[i]for i in [0,1,4,5]),[0,1,2,3])
        self.load_sector(4);self.assertEqual(self.read(0x404),29)
        self.assertTrue(self.s[0x446]&1)

    def test_shutdown_saves_people_once_and_counts_as_withdrawal(self):
        self.save_sector(0);self.s[0x448]|=16
        self.lib.ng_shutdown();self.lib.ng_cache();self.lib.ng_outcome()
        self.assertEqual(self.state[38]&1,1)
        self.assertEqual(self.state[15],1)
        self.assertGreater(self.state[42]|self.state[43]<<8,0)
        before=bytes(self.state[42:50]);self.lib.ng_shutdown();self.assertEqual(bytes(self.state[42:50]),before)

    def test_computer_future_tower_shutdown_preserves_saved_people(self):
        self.state[13]=3;self.state[14]=15;self.s[0x448]|=16
        self.buffers['owned'][0]=2
        self.lib.ng_rule(34,5000,1,0)
        self.assertTrue(self.s[0x448]&32)
        self.assertEqual(self.read(0x3fe),4)
        self.assertEqual(self.state[42]|self.state[43]<<8,101)

    def test_shield_repairs_selected_building_and_only_pays_when_damaged(self):
        self.word(0x122,1);self.word(0x3d6,40)
        self.s[0x19c:0x19c+10]=bytes([255,0])*5
        self.assertEqual(self.lib.ng_repair(0,0),1)
        self.assertEqual(self.read(0x3d6),90)
        self.assertEqual(self.lib.ng_repair(0,0),1)
        self.assertEqual(self.read(0x3d6),100)
        self.assertEqual(self.lib.ng_repair(0,0),0)
        self.assertEqual(self.lib.ng_repair(0,1),0)

    def test_late_shield_uses_factory_inventory(self):
        self.word(0x122,16);self.word(0xee,1);self.word(0x3d6,1)
        self.assertEqual(self.lib.ng_repair(4,0),1)
        self.assertEqual(self.read(0xee),0)
        self.assertEqual(self.read(0x3d6),100)
        self.word(0x3d6,1);self.assertEqual(self.lib.ng_repair(4,0),0)

    def test_original_island_faction_count_limits_initial_towers(self):
        self.word(0x3fe,4);self.s[0x446]=0;self.word(0x2fc,0);self.word(0x404,0);self.word(0x406,0)
        self.save_sector(0);self.save_sector(1);self.save_sector(4);self.save_sector(5)
        ctypes.c_uint8.in_dll(self.lib,'world_factions').value=2
        self.state[127]=0;self.state[126]=0;self.lib.ng_prepare_island()
        owners=(ctypes.c_uint8*16).in_dll(self.lib,'ng_owners')
        self.assertEqual(self.state[14],3)
        self.assertEqual(owners[0],0)
        self.assertEqual(sorted(owners[i]for i in [0,1,4,5]),[0,1,4,4])

    def test_selected_human_faction_survives_two_player_island_transition(self):
        self.word(0x3fe,4);self.s[0x446]=0;self.word(0x2fc,0);self.word(0x404,0);self.word(0x406,0)
        self.save_sector(0);self.save_sector(1);self.save_sector(4)
        ctypes.c_uint8.in_dll(self.lib,'world_factions').value=2
        self.state[13]=3;self.state[127]=0;self.state[126]=0;self.lib.ng_prepare_island()
        owners=(ctypes.c_uint8*16).in_dll(self.lib,'ng_owners')
        self.assertEqual(owners[0],3)
        self.assertEqual(sorted(owners[i]for i in [0,1,4]),[0,3,4])
        self.assertEqual(self.state[14],9)

    def test_ground_route_crosses_friendly_sectors_but_stops_at_neutral_endpoints(self):
        for i in [0,1,2,3]:self.save_sector(i)
        self.load_sector(0);self.buffers['army'][10]=10;self.lib.ng_rule(20,0,0,0);self.lib.ng_cache()
        self.load_sector(2);self.word(0x3fe,4);self.lib.ng_cache()
        self.assertEqual(self.lib.ng_route_mask(0,0),7)
        self.assertEqual(self.lib.ng_move(0,3,0),0)
        self.assertEqual(self.lib.ng_move(0,2,0),1)
        self.assertEqual(self.lib.ng_route_mask(2,0),15)
        self.assertEqual(self.lib.ng_move(2,3,0),1)
        self.load_sector(3);self.assertEqual(self.s[0x2c8+10],10)

    def test_allied_corridor_and_enemy_occupation_of_neutral_land(self):
        for i in [0,1,2]:self.save_sector(i)
        self.load_sector(1);self.word(0x3fe,1);self.lib.ng_cache()
        self.assertEqual(self.lib.ng_route_mask(0,0),3)
        self.lib.ng_rule(43,0,1,0)
        self.assertEqual(self.lib.ng_route_mask(0,0),7)
        self.word(0x3fe,4);self.buffers['army'][10]=1;self.lib.ng_rule(20,2,0,0);self.lib.ng_cache()
        self.assertEqual(self.lib.ng_route_mask(0,0),3)

    def test_exhausted_campaign_pool_has_no_active_factions(self):
        self.state[15]=1;self.state[116]=self.state[117]=0
        self.assertEqual(self.lib.ng_campaign_action(ord('N')),1)
        self.assertEqual(self.state[15],2)
        self.lib.ng_prepare_island()
        self.assertEqual(self.state[14],0)

    def test_original_ai_repair_skips_mine_when_absent_factory_halves_index(self):
        persona=(ctypes.c_uint8*56).in_dll(self.lib,'gp_personality');persona[:]=bytes(56)
        for b in range(4):persona[16+b*2]=100
        self.s[0x446]=3;self.word(0x2fc,2);self.word(0x3d6,100);self.word(0x3d8,1)
        self.word(0x122,1);self.word(0xe6,3)
        seed=bytes(self.state[26:28]);self.lib.ng_rule(52,0,0,0)
        self.assertEqual(self.read(0x3d8),1)
        self.assertEqual(self.read(0xe6),3)
        self.assertEqual(bytes(self.state[26:28]),seed)

    def test_original_ai_repair_consumes_batch_but_heals_once_per_shield_age(self):
        persona=(ctypes.c_uint8*56).in_dll(self.lib,'gp_personality');persona[:]=bytes(56)
        for b in range(4):persona[16+b*2]=100;self.word(0x3d6+b*2,100)
        self.s[0x446]=15;self.word(0x2fc,4);self.word(0x3d8,1)
        self.word(0x122,1);self.word(0xe6,3)
        self.lib.ng_rule(52,0,0,0)
        self.assertEqual(self.read(0xe6),1)
        self.assertEqual(self.read(0x3d8),51)

    def expedition_persona(self):
        persona=(ctypes.c_uint8*56).in_dll(self.lib,'gp_personality');persona[:]=bytes(56)
        for at,n in [(0x18,100),(0x1a,125),(0x1c,125),(0x1e,20),(0x20,20)]:persona[at]=n

    def empty_sector(self,index,owner=4):
        self.s[:]=bytes(0x449);self.s[0x3b8:0x3c2]=bytes([255])*10
        self.word(0x3fe,owner);self.s[0x448]=128;self.word(0xbe,65535);self.word(0xd2,65535);self.save_sector(index)

    def test_expedition_forms_requested_force_and_pays_people(self):
        self.save_sector(0);self.empty_sector(1);self.load_sector(0);self.expedition_persona()
        self.assertEqual(self.lib.ng_expedition(),1)
        self.load_sector(0);self.assertEqual(self.read(0x404),80);self.assertEqual(self.read(0x406),80)
        self.load_sector(1);self.assertEqual(self.s[0x2c8+10],20)

    def test_expedition_cannot_send_unarmed_force_across_water(self):
        self.save_sector(0);self.empty_sector(15);self.load_sector(0);self.expedition_persona()
        self.assertEqual(self.lib.ng_expedition(),0)
        self.assertEqual(self.read(0x404),100);self.assertEqual(self.read(0x406),100)
        self.load_sector(15);self.assertEqual(self.read(0x2f4),0)

    def test_expedition_nuclear_fallback_sets_source_and_consumes_inventory(self):
        ctypes.c_uint8.in_dll(self.lib,'world_first').value=6;ctypes.c_uint8.in_dll(self.lib,'world_last').value=9
        self.word(0x11e,1);self.save_sector(0);self.empty_sector(15);self.load_sector(0);self.expedition_persona()
        self.assertEqual(self.lib.ng_expedition(),1)
        self.load_sector(0);self.assertEqual(self.read(0x11e),0)
        self.load_sector(15);self.assertGreaterEqual(self.s[0x444],100);self.assertLess(self.s[0x444],140);self.assertEqual(self.read(0x440),0)

    def test_roaming_army_leaves_neutral_sector_without_a_tower(self):
        self.state[13]=1
        personas=(ctypes.c_uint8*224).in_dll(self.lib,'world_personalities');personas[0x28]=100
        self.word(0x3fe,4);self.buffers['army'][10]=30;self.lib.ng_rule(20,0,0,0);self.save_sector(0)
        self.empty_sector(1,0);self.load_sector(0)
        self.assertEqual(self.lib.ng_roam(),1);self.assertEqual(self.state[39],3)
        self.load_sector(0);self.assertEqual(self.read(0x2f4),0)
        self.load_sector(1);self.assertEqual(self.read(0x2f4),30)

    def test_peacetime_demobilization_returns_unarmed_before_weapons(self):
        persona=(ctypes.c_uint8*56).in_dll(self.lib,'gp_personality');persona[0x2e]=50
        self.buffers['army'][0]=10;self.buffers['army'][10]=10;self.lib.ng_rule(20,0,0,0);self.save_sector(0)
        self.assertEqual(self.lib.ng_demobilize(1),1)
        self.assertEqual(self.s[0x2c8],10);self.assertEqual(self.s[0x2c8+10],0);self.assertEqual(self.read(0x404),110)

    def test_live_ai_processes_field_armies_and_obeys_roaming_cooldown(self):
        self.state[13]=1
        personas=(ctypes.c_uint8*224).in_dll(self.lib,'world_personalities');personas[0x28]=100
        self.word(0x3fe,4);self.buffers['army'][10]=30;self.lib.ng_rule(20,0,0,0);self.save_sector(0)
        self.empty_sector(1,0);self.load_sector(0);self.state[39]=1
        self.lib.ng_step(30);self.assertEqual(self.read(0x2f4),30);self.assertEqual(self.state[39],0)
        self.lib.ng_step(30);self.load_sector(1);self.assertEqual(self.read(0x2f4),30)
