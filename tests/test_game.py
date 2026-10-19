import re, subprocess, sys, unittest
from pathlib import Path
from cpu6502 import CPU
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))

def boot(cpu,sym,pal=True,max_steps=3000000):
 """Run the real power-on path: BASIC SYS -> start -> title screen -> main_loop.
 Raster IRQs fire like the VIC would; a key press dismisses the title after a few frames."""
 cpu.m[0x02a6]=1 if pal else 0
 cpu.pc=sym['start']
 seen=[0]
 def press(c):
  if c.pc==sym['title_wait']:
   seen[0]+=1
   if seen[0]==12:c.key=ord(' ')
 cpu.run_until(sym['main_loop'],max_steps=max_steps,on_pc=press)
 return cpu

def symbol_table():
 return {v:int(addr,16) for addr,v in (ln.split() for ln in (ROOT/'dist/symbols.txt').read_text().splitlines())}
class StrategyTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  subprocess.run([sys.executable,str(ROOT/'tools/asm6502.py'),str(ROOT/'src/main.asm'),'-o',str(ROOT/'dist/MegaLoMania64.prg'),'--symbols',str(ROOT/'dist/symbols.txt')],cwd=ROOT,check=True,capture_output=True)
  cls.sym=symbol_table()
 def setUp(self):
  self.cpu=CPU(ROOT/'dist/MegaLoMania64.prg')
  self.cpu.call(self.sym['new_game'])
 def state(self,name,idx=None):return self.cpu.m[self.sym[name]+(idx or 0)]
 def put(self,name,v,idx=None):self.cpu.m[self.sym[name]+(idx or 0)]=v
 def call(self,name):return self.cpu.call(self.sym[name])
 def press(self,key):self.cpu.key=ord(key) if isinstance(key,str) else key;self.call('read_keys')
 def test_prg_memory_layout(self):
  assert self.sym['start']==0x1000
  assert self.sym['cpu_count'] < 0x3700
  assert len((ROOT/'assets/charset.bin').read_bytes())==2048
  assert len((ROOT/'assets/cursor_sprite.bin').read_bytes())==64
  assert self.cpu.m[0x07f8]==0xdc
  hardware=boot(CPU(ROOT/'dist/MegaLoMania64.prg'),self.sym)
  self.assertEqual(hardware.m[0xd018],0x1e)
  self.assertEqual(hardware.m[0xd016],0x18)
  self.assertEqual(hardware.m[0xd021],6)
  self.assertEqual(hardware.m[0x07f8],0xdc)
 def test_d64_exact_chain(self):
  from make_d64 import verify_image
  image=ROOT/'dist/MegaLoMania64.d64'
  from make_d64 import make_image
  make_image(ROOT/'dist/MegaLoMania64.prg',image)   # always rebuild: never validate a stale image
  original=(ROOT/'dist/MegaLoMania64.prg').read_bytes()
  self.assertEqual(verify_image(image,original),original)
 def test_initial_state_and_render(self):
  self.assertEqual(self.state('owner',0),1)
  self.assertEqual(self.state('owner',11),2)
  self.assertEqual(self.state('owner',3),3)
  self.assertEqual(self.state('owner',8),4)
  self.assertEqual(self.state('you_count'),1)
  self.assertEqual(self.state('cpu_count'),3)
  self.assertEqual(self.cpu.m[0x400],ord('M'))
  self.assertEqual(self.cpu.m[0x401],ord('E'))
  self.assertEqual(self.cpu.m[0x0400+3*40+1],6) # coast mask corner # biome base or detail tile
 def test_navigation_and_capture(self):
  self.press('D')
  self.assertEqual(self.state('selected'),1)
  self.press('X')
  self.assertEqual(self.state('owner',1),1)
  self.assertEqual(self.state('people',0),13)
  self.assertEqual(self.state('people',1),8) # 25/2 -> 12/2+2
  self.assertEqual(self.state('you_count'),2)
  self.press('S')
  self.assertEqual(self.state('selected'),5)
  self.press('X') # source 0 not adjacent -> reject
  self.assertEqual(self.state('owner',5),0)
 def test_mine_research_weapons_fort(self):
  self.press('M');self.press('R')
  self.assertEqual(self.state('miners',0),3)
  self.assertEqual(self.state('labs',0),3)
  self.press('P')
  self.assertEqual(self.state('weapons',0),7)
  self.assertEqual(self.state('ore',0),12)
  self.put('ore',20,0)
  self.press('F')
  self.assertEqual(self.state('fort',0),2)
  self.assertEqual(self.state('ore',0),8)
  vein_before=self.state('vein',0)
  self.call('simulate')
  self.assertEqual(self.state('ore',0),12)
  self.assertEqual(self.state('vein',0),vein_before-4)
  for _ in range(7):self.call('simulate')
  self.assertGreaterEqual(self.state('level',0),1)
 def test_ai_source_restored_and_expansion(self):
  self.press('D');self.press(13)
  self.assertEqual(self.state('source'),1 if self.state('owner',1)==1 else 0) # ENTER on free fails
  self.press('A');self.press(13)
  saved=self.state('source');sel=self.state('selected')
  self.call('ai_turn')
  self.assertEqual(self.state('source'),saved)
  self.assertEqual(self.state('selected'),sel)
  self.assertEqual(sum(1 for i in range(12) if self.state('owner',i)>1),4)
 def test_pause_and_restart(self):
  self.press('D');self.press('X')
  self.press(' ')
  self.assertEqual(self.state('state'),1)
  self.press(' ')
  self.assertEqual(self.state('state'),0)
  self.press('N')
  self.assertEqual(self.state('owner',1),0)
  self.assertEqual(self.state('selected'),0)
 def test_adjacency_at_row_boundary(self):
  self.put('source',3);self.put('selected',4)
  self.call('adjacent')
  self.assertFalse(self.cpu.flag(1))
  self.put('source',3);self.put('selected',7)
  self.call('adjacent')
  self.assertTrue(self.cpu.flag(1))
 def test_no_enemy_job_sabotage(self):
  self.put('selected',11)
  old_m=self.state('miners',11);old_r=self.state('labs',11)
  self.press('J');self.press('K')
  self.assertEqual(self.state('miners',11),old_m)
  self.assertEqual(self.state('labs',11),old_r)
 def test_endgames(self):
  for i in range(12):self.put('owner',1,i)
  self.put('owner',1,1)
  self.put('source',0);self.put('selected',1)
  self.put('people',40,0)
  self.put('people',0,1)
  self.call('draw_score')
  self.assertEqual(self.state('you_count'),12)
  self.assertEqual(self.state('state'),2)
  self.press('N')
  for i in range(12):self.put('owner',2,i)
  self.put('owner',1,0);self.put('owner',2,4)
  self.put('people',50,4);self.put('people',4,0)
  self.put('weapons',30,4);self.put('weapons',0,0)
  self.put('source',4);self.put('selected',0);self.put('attacking',2)
  self.put('fort',0,0);self.put('level',0,0)
  self.call('do_attack');self.call('draw_score')
  self.assertEqual(self.state('state'),3)
  self.assertEqual(self.state('you_count'),0)
 def test_small_outpost_can_recover(self):
  self.put('people',4,0)
  self.put('miners',2,0);self.put('labs',2,0)
  self.put('ticks',7)
  self.call('simulate')
  self.assertEqual(self.state('people',0),5)
  self.assertEqual(self.state('miners',0)+self.state('labs',0),0)
 def test_printable_messages_fit(self):
  text=''.join(f.read_text() for f in sorted((ROOT/'src').glob('*.asm')))
  for name,msg in re.findall(r'(?m)^(\w+):\s*!text "([^"]+)",0',text):
   if name.startswith(('msg_','help_','ttl_')):
    self.assertLessEqual(len(msg),40,(name,len(msg)))
 def test_mass_progress_no_overflow(self):
  self.put('labs',12,0);self.put('research',23,0)
  self.call('simulate')
  self.assertEqual(self.state('research',0),11)
  self.assertEqual(self.state('level',0),1)
  self.put('people',90,0);self.put('ore',95,0)
  self.call('simulate')
  self.assertEqual(self.state('people',0),90)
  self.assertEqual(self.state('ore',0),95)

 def test_camp_28_unique_maps_and_10_epochs(self):
  maps=set()
  for stage in range(28):
   self.put('campaign_island',stage)
   self.call('load_island')
   self.assertEqual(self.state('campaign_island'),stage)
   self.assertEqual(self.state('epoch'),min(stage//3,9))
   self.assertEqual(sum(self.state('owner',i)==1 for i in range(12)),1)
   self.assertEqual(sorted(self.state('owner',i) for i in range(12) if self.state('owner',i)>1),[2,3,4])
   self.assertTrue(all(1<=self.state('terrain',i)<=5 for i in range(12)))
   self.assertTrue(all(0<=self.state('vein',i)<=95 for i in range(12)))
   maps.add(tuple(self.state('terrain',i) for i in range(12)))
  self.assertEqual(len(maps),28)
 def test_28_stage_end_to_end_victory(self):
  for stage in range(28):
   self.assertEqual(self.state('campaign_island'),stage)
   for i in range(12):self.put('owner',1,i)
   self.call('draw_score')
   self.assertEqual(self.state('state'),4 if stage==27 else 2)
   if stage<27:
    self.press('C')
    self.assertEqual(self.state('state'),0)
  self.press(' ')
  self.assertEqual(self.state('state'),4) # final cannot be unpaused
  self.press('N')
  self.assertEqual(self.state('campaign_island'),0)
  self.assertEqual(self.state('state'),0)
 def test_stage_code_and_invalid_recovery(self):
  self.press('L');self.assertEqual(self.state('load_mode'),1)
  self.press('2');self.assertEqual(self.state('load_mode'),2)
  self.press('8')
  self.assertEqual(self.state('campaign_island'),27)
  self.assertEqual(self.state('epoch'),9)
  self.assertEqual(self.state('reserve'),90)
  self.assertEqual(self.state('load_mode'),0)
  self.press('L');self.press('2');self.press('9')
  self.assertEqual(self.state('load_mode'),0)
  self.assertEqual(self.state('campaign_island'),27)
  self.press('L');self.press('N')
  self.assertEqual(self.state('load_mode'),0)
 def test_buildings_and_research_gating(self):
  self.press('D');self.press('X')
  self.assertEqual(self.state('owner',1),1)
  self.assertEqual(self.state('buildings',1),1)
  self.press(13)
  self.press('R')
  self.assertEqual(self.state('labs',1),0) # lab must be built
  self.press('P')
  self.assertEqual(self.state('weapons',1),6) # captured troops carry starting weapons
  for _ in range(12):self.call('simulate')
  self.assertGreaterEqual(self.state('ore',1),12)
  self.press('V')
  self.assertEqual(self.state('buildings',1),3)
  self.press('R')
  self.assertEqual(self.state('labs',1),1)
  self.press('G')
  self.assertEqual(self.state('buildings',1),3) # must mine ore again
  for _ in range(8):self.call('simulate')
  self.press('G')
  self.assertEqual(self.state('buildings',1),7)
  self.press('B')
  self.assertEqual(self.state('minegrade',1),0) # insufficient ore
  for _ in range(9):self.call('simulate')
  self.press('B')
  self.assertEqual(self.state('minegrade',1),1)
 def test_joystick_rising_edge(self):
  self.put('joy_raw',0xf7)    # port2 RIGHT held (sampled by the IRQ)
  self.call('read_keys')
  self.assertEqual(self.state('selected'),1)
  self.call('read_keys')
  self.assertEqual(self.state('selected'),1)
  self.put('joy_raw',0xff)
  self.call('read_keys')
  self.put('joy_raw',0xf7)
  self.call('read_keys')
  self.assertEqual(self.state('selected'),2)
 def test_map_render_safe_memory_and_sprite(self):
  for stage in (0,4,10,19,27):
   self.put('campaign_island',stage)
   self.call('load_island')
   self.assertEqual(self.cpu.m[0x07f8],0xdc)
   self.assertTrue(all(self.cpu.m[0x0400+i]<=255 for i in range(1000)))
   self.assertTrue(all(self.cpu.m[0xd800+i]<=15 for i in range(1000)))
 def test_pal_and_ntsc_scheduler(self):
  # $02A6 is the PAL/NTSC KERNAL flag and is only read at actual program boot
  ntsc=boot(CPU(ROOT/'dist/MegaLoMania64.prg'),self.sym,pal=False)
  self.assertEqual(ntsc.m[self.sym['frames_per_tick']],29)
  pal=boot(CPU(ROOT/'dist/MegaLoMania64.prg'),self.sym,pal=True)
  self.assertEqual(pal.m[self.sym['frames_per_tick']],24)
 def test_single_survivor_rebuilds_population(self):
  self.put('people',1,0)
  self.put('miners',0,0)
  self.put('labs',0,0)
  self.put('ticks',7)
  self.call('simulate')
  self.assertEqual(self.state('people',0),2)
 def test_long_running_sector_bounds(self):
  # Simulate strategic pressure without forcing impossible wins; check caps and
  # ownership invariants across three generations of map difficulty.
  for stage in (0,12,27):
   self.put('campaign_island',stage)
   self.call('load_island')
   for _ in range(96):
    if self.state('state')!=0:break
    self.call('simulate')
    for idx in range(12):
     self.assertIn(self.state('owner',idx),(0,1,2,3,4))
     self.assertLessEqual(self.state('people',idx),90)
     self.assertLessEqual(self.state('ore',idx),95)
     self.assertLessEqual(self.state('fort',idx),9)
     self.assertLessEqual(self.state('level',idx),5)
     self.assertLessEqual(self.state('minegrade',idx),2)
 def test_four_rivals_have_distinct_spawn_and_render_colors(self):
  for stage in range(28):
   self.put('campaign_island',stage);self.call('load_island')
   pos={f:next(i for i in range(12) if self.state('owner',i)==f) for f in (1,2,3,4)}
   self.assertEqual(len(set(pos.values())),4)
   for fac,ink in ((1,13),(2,10),(3,14),(4,9)):
    sid=pos[fac]
    # Interior tile, unaffected by coastline, building silhouette or population
    x=[1,8,15,22][sid%4];y=[3,9,15][sid//4]
    self.assertEqual(self.cpu.m[0xd800+(y+2)*40+x],ink)

 def test_friendly_attack_protection_and_reinforcement(self):
  self.press('D');self.press('X')
  self.assertEqual(self.state('owner',1),1)
  self.put('people',40,0);self.put('people',25,1)
  self.put('weapons',9,0);self.put('weapons',5,1)
  self.put('buildings',7,1)
  self.put('ore',40,1)
  self.press('X') # must not annex / erase friendly buildings
  self.assertEqual(self.state('people',1),25)
  self.assertEqual(self.state('buildings',1),7)
  self.press('H')
  self.assertEqual(self.state('people',0),20)
  self.assertEqual(self.state('people',1),45)
  self.assertEqual(self.state('weapons',0),5)
  self.assertEqual(self.state('weapons',1),9)
  self.assertEqual(self.state('buildings',1),7)
  self.assertEqual(self.state('ore',1),40)
  self.put('people',89,1)
  self.press('H')
  self.assertEqual(self.state('people',1),90)
  self.assertEqual(self.state('people',0),19)

 def test_cannot_reinforce_enemy_or_nonadjacent(self):
  self.put('people',45,0)
  self.put('selected',11)
  self.press('H')
  self.assertEqual(self.state('people',0),45)
  self.put('selected',3)
  self.press('H')
  self.assertEqual(self.state('people',0),45)
  self.put('source',3)  # AI sector can't send to human base
  self.put('selected',0)
  self.press('H')
  self.assertEqual(self.state('people',0),45)

 def test_automated_production_and_fortification(self):
  self.press('Y');self.press('Z')
  self.assertEqual(self.state('policy',0),3)
  self.put('ore',90,0)
  self.put('weapons',8,0)
  self.put('fort',1,0)
  self.call('simulate')
  self.assertEqual(self.state('weapons',0),9)
  self.assertEqual(self.state('fort',0),2)
  self.assertLess(self.state('ore',0),90)
  self.press('Y');self.press('Z')
  self.assertEqual(self.state('policy',0),0)
  self.put('selected',11)
  self.press('Y');self.press('Z')
  self.assertEqual(self.state('policy',11),0)

 def test_ai_all_three_factions_act_without_stealing_selection(self):
  before={fac:sum(self.state('owner',i)==fac for i in range(12)) for fac in (2,3,4)}
  self.put('selected',5);self.put('source',0)
  for _ in range(3):
   self.call('ai_turn')
   self.assertEqual(self.state('selected'),5)
   self.assertEqual(self.state('source'),0)
  after={fac:sum(self.state('owner',i)==fac for i in range(12)) for fac in (2,3,4)}
  self.assertTrue(all(after[f]>=before[f] for f in (2,3,4)))
  self.assertEqual(sum(after.values()),6)

 def test_ai_vs_ai_combat_and_winner_ownership(self):
  # Any AI pair can battle, no hardwired #2 capture code.
  self.put('owner',4,1)
  self.put('owner',3,0)
  self.put('people',80,0)
  self.put('people',4,1)
  self.put('weapons',40,0)
  self.put('weapons',0,1)
  self.put('level',5,0)
  self.put('fort',0,1)
  self.put('level',0,1)
  self.put('source',0);self.put('selected',1)
  self.put('attacking',3)
  self.call('do_attack')
  self.assertEqual(self.state('owner',1),3)

 def test_coastline_vic_and_cpu_bounds(self):
  base=self.sym['coast_mask']
  mask=[self.cpu.m[base+i] for i in range(30)]
  self.assertEqual(len(mask),30)
  self.assertTrue(0 in mask and 1 in mask)
  self.assertEqual(self.cpu.m[0xd018],0)  # until start executed
  booted=boot(CPU(ROOT/'dist/MegaLoMania64.prg'),self.sym)
  self.assertEqual(booted.m[0xd018],0x1e)
  self.assertEqual(booted.m[0x07f8],0xdc)
  self.assertEqual(booted.m[0x07f9],0xdd)
  self.assertLess(self.sym['cpu_count'],0x3700)
  self.assertTrue(any(booted.m[0x3800+6*8+k] for k in range(8))) # water glyph

 def test_heavy_assault_can_overcome_max_ai_fortification(self):
  def setup():
   self.put('selected',1);self.put('source',0)
   self.put('owner',2,1)
   self.put('people',80,0);self.put('weapons',40,0);self.put('level',5,0)
   self.put('people',90,1);self.put('fort',4,1);self.put('weapons',30,1);self.put('level',5,1)
  setup()
  self.press('X')
  self.assertEqual(self.state('owner',1),2)   # ordinary raid blocked
  self.assertEqual(self.state('people',1),70) # but siege weakens target
  self.assertEqual(self.state('fort',1),3)
  self.assertEqual(self.state('weapons',1),29)
  self.assertEqual(self.state('heavy'),0)
  setup()
  self.press('T')
  self.assertEqual(self.state('owner',1),1)   # high-risk attack succeeds
  self.assertEqual(self.state('people',0),20)
  self.assertEqual(self.state('heavy'),0)

 def test_capture_clears_automation_and_keeps_resource_vein(self):
  self.put('selected',1)
  self.put('owner',2,1)
  self.put('people',80,0)
  self.put('weapons',40,0)
  self.put('people',5,1)
  self.put('policy',3,1)
  original_vein=self.state('vein',1)
  self.press('X')
  self.assertEqual(self.state('owner',1),1)
  self.assertEqual(self.state('policy',1),0)
  self.assertEqual(self.state('vein',1),original_vein)

 def test_all_screen_plot_coordinates_are_in_bounds(self):
  # Dynamic instrumentation for actual native JSR plot, not only RAM byte ranges.
  for stage in (0,7,14,21,27):
   cpu=CPU(ROOT/'dist/MegaLoMania64.prg')
   cpu.m[self.sym['campaign_island']]=stage
   cpu.push(0xff);cpu.push(0xef);cpu.pc=self.sym['load_island']
   count=0;seen=0
   while cpu.pc!=0xfff0:
    if cpu.pc==self.sym['plot']:
     seen+=1
     self.assertLess(cpu.x,40,('x overflow',stage,cpu.x))
     self.assertLess(cpu.y,25,('y overflow',stage,cpu.y))
    cpu.step();count+=1
    self.assertLess(count,400000)
   self.assertGreater(seen,900)

 def test_graphics_era_towers_are_baked_in_charset(self):
  chars=(ROOT/'assets/charset.bin').read_bytes()
  self.assertTrue(all(any(chars[g*8:(g+1)*8]) for g in range(17,25)))
  self.assertEqual(len(chars),2048)

 def test_doctrine_permission_and_wrap(self):
  self.assertEqual(self.state('doctrine',0),0)
  self.press('Q');self.assertEqual(self.state('doctrine',0),1)
  self.press('Q');self.assertEqual(self.state('doctrine',0),2)
  self.press('Q');self.assertEqual(self.state('doctrine',0),0)
  self.put('selected',11);initial=self.state('doctrine',11)
  self.press('Q');self.assertEqual(self.state('doctrine',11),initial)
 def test_variable_research_cost(self):
  self.put('level',1,0);self.put('research',23,0)
  self.put('labs',1,0);self.put('ticks',1)
  self.call('simulate')
  self.assertEqual(self.state('level',0),1)
  self.assertEqual(self.state('research',0),24)
  self.put('research',31,0);self.call('simulate')
  self.assertEqual(self.state('level',0),2)
  self.assertEqual(self.state('research',0),0)
 def test_industry_doctrine_gains_extra_mining(self):
  self.put('level',2,0);self.put('ore',0,0);self.put('miners',2,0)
  self.put('doctrine',0,0);self.put('ticks',1)
  self.call('simulate'); self.assertEqual(self.state('ore',0),5) # 2 miners+1 minegrade+2
  self.put('ore',0,0);self.put('doctrine',1,0)
  self.call('simulate');self.assertEqual(self.state('ore',0),3)
 def test_ai_adapts_workforce(self):
  self.put('people',50,11)
  self.put('miners',1,11);self.put('labs',0,11)
  self.put('buildings',7,11)
  self.call('simulate')
  self.assertEqual(self.state('miners',11),2)
  self.assertEqual(self.state('labs',11),1)
 def test_save_load_roundtrip(self):
  self.press('D');self.press('X')
  self.put('ore',73,0);self.put('level',3,0)
  self.put('doctrine',2,0)
  saved={k:bytes(self.cpu.m[self.sym[k]:self.sym[k]+12]) for k in ('owner','people','vein','ore','level','doctrine')}
  self.press('O')
  self.assertIn('ML64SAVE',self.cpu.drive_files)
  blob=self.cpu.drive_files['ML64SAVE']
  self.assertEqual(blob[2:6],b'ML64')
  self.press('N')
  self.assertNotEqual(self.state('owner',1),1)
  self.press('I')
  for k,v in saved.items():self.assertEqual(bytes(self.cpu.m[self.sym[k]:self.sym[k]+12]),v)
  self.assertEqual(self.state('selected'),1)
  self.assertEqual(self.state('source'),0)
 def test_disk_load_corrupt_rejected_without_partial_mutation(self):
  self.press('O')
  valid=self.cpu.drive_files['ML64SAVE']
  self.put('ore',47,0)
  bad=bytearray(valid);bad[10]^=0x80
  self.cpu.drive_files['ML64SAVE']=bytes(bad)
  self.press('I')
  self.assertEqual(self.state('ore',0),47)
  self.assertEqual(self.state('campaign_island'),0)
  self.cpu.drive_files['ML64SAVE']=valid
  self.press('I')
  self.assertEqual(self.state('ore',0),16)
 def test_save_load_cross_epoch_and_clock(self):
  for ch in ('L','2','8'):self.press(ch)
  self.assertEqual(self.state('campaign_island'),27)
  self.put('ore',42,self.state('selected'))
  self.press('O')
  self.press('N')
  self.cpu.m[0x02a6]=0 # NTSC
  self.press('I')
  self.assertEqual(self.state('campaign_island'),27)
  self.assertEqual(self.state('epoch'),9)
  self.assertEqual(self.state('frames_per_tick'),29)
  self.assertEqual(self.state('ore',self.state('selected')),42)


 def test_missing_disk_file_does_not_mutate_campaign(self):
  self.put('ore',61,0)
  self.press('I')
  self.assertEqual(self.state('ore',0),61)
  self.assertEqual(self.state('campaign_island'),0)
 def test_snapshot_range_validation_even_with_valid_checksums(self):
  self.press('O')
  blob=bytearray(self.cpu.drive_files['ML64SAVE'])
  start=8 # 2-byte PRG header, 6-byte ML64 preamble, then owner[0]
  blob[start]=9 # invalid owner; recompute both checksums
  n=blob[7]
  payload=blob[8:8+n]
  blob[8+n]=__import__('functools').reduce(lambda a,b:a^b,payload,0)
  blob[9+n]=sum(payload)&255
  self.cpu.drive_files['ML64SAVE']=bytes(blob)
  self.put('ore',65,0)
  self.press('I')
  self.assertEqual(self.state('ore',0),65)
 def test_load_forced_c000_ignores_modified_prg_address(self):
  self.press('O')
  blob=bytearray(self.cpu.drive_files['ML64SAVE'])
  blob[0:2]=bytes((1,8)) # misleading file address $0801
  self.cpu.drive_files['ML64SAVE']=bytes(blob)
  self.put('ore',38,0)
  self.press('I')
  self.assertEqual(self.state('ore',0),16)
  self.assertEqual(self.cpu.m[0x0801],11)

if __name__=='__main__':unittest.main()
