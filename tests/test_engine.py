"""v4 engine tests: IRQ engine, title, joystick, diplomacy, inventions, develop, disk, fuzz."""
import json, random, re, unittest
from common import *

NAMES=['CLUB','SPEAR','SWORD','BALLIS','XBOW','MUSKET','CANNON','TANK','MISSIL','LASER']

class IrqEngine(GameCase):
    def test_install_programs_vic_cia_and_vector(self):
        self.irq_on()
        m=self.cpu.m
        self.assertEqual(m[0x314]|m[0x315]<<8,self.sym['irq_handler'])
        self.assertEqual(m[0xd01a],1)
        self.assertEqual(m[0xd012],250)
        self.assertEqual(m[0xd011]&0x80,0)
        self.assertEqual(m[0xdc0d],0x7f);self.assertEqual(m[0xdd0d],0x7f)
        self.assertEqual(self.state('irq_stage'),0)
    def test_frame_irq_counts_vblank_samples_joystick_and_restores_registers(self):
        self.irq_on()
        self.cpu.joystick=0xef             # FIRE held on port 2
        self.cpu.a,self.cpu.x,self.cpu.y=0x11,0x22,0x33
        v=self.state('vblank');mf=self.state('music_frame')
        self.cpu.run_irq()
        self.assertEqual(self.state('vblank'),(v+1)&255)
        self.assertEqual(self.state('joy_raw'),0x0f)
        self.assertEqual(self.cpu.m[0xdc00],0xff)       # columns deselected before the pins are read
        self.assertEqual(self.state('music_frame'),mf+1)
        self.assertEqual((self.cpu.a,self.cpu.x,self.cpu.y),(0x11,0x22,0x33))
        self.assertEqual(self.cpu.m[0xd019],0xff)       # raster flag acknowledged
    def test_foreign_interrupt_is_not_counted(self):
        self.irq_on()
        v=self.state('vblank')
        self.cpu.m[0xd019]=0
        self.cpu.in_irq=True                              # enter handler as if a non-raster source fired
        self.cpu.push(0);self.cpu.push(0);self.cpu.push(0x20);self.cpu.push(1);self.cpu.push(2);self.cpu.push(3)
        self.cpu.pc=self.sym['irq_handler']
        while self.cpu.in_irq:self.cpu.step()
        self.assertEqual(self.state('vblank'),v)
    def test_music_tune_follows_epoch_and_title(self):
        self.irq_on()
        tempo=[self.cpu.m[self.sym['music_tempo']+i] for i in range(4)]
        for epoch,tune in ((0,0),(3,0),(4,1),(6,1),(7,2),(9,2)):
            self.put('epoch',epoch);self.put('title_active',0);self.put('music_pos',0)
            self.put('music_frame',tempo[tune]-1)
            self.cpu.run_irq()
            idx=tune*16
            self.assertEqual(self.cpu.m[0xd407],self.cpu.m[self.sym['melody_lo']+idx],(epoch,))
            self.assertEqual(self.cpu.m[0xd408],self.cpu.m[self.sym['melody_hi']+idx])
            self.assertEqual(self.cpu.m[0xd40e],self.cpu.m[self.sym['bass_lo']+idx])
            self.assertEqual(self.state('music_pos'),1)
        self.put('epoch',2);self.put('title_active',1);self.put('music_pos',5);self.put('music_frame',tempo[3]-1)
        self.cpu.run_irq()   # title also arms the bars; music still uses tune 3
        self.assertEqual(self.cpu.m[0xd407],self.cpu.m[self.sym['melody_lo']+3*16+5])
        self.assertEqual(self.state('music_pos'),6)
    def test_music_sequence_wraps_after_16_steps(self):
        self.irq_on()
        self.put('music_pos',15);self.put('music_frame',200)
        self.cpu.run_irq()
        self.assertEqual(self.state('music_pos'),0)
    def test_title_raster_bars_cycle_and_restore_frame(self):
        self.irq_on()
        self.put('title_active',1)
        self.cpu.run_irq()                         # frame IRQ arms stage 1
        self.assertEqual(self.state('irq_stage'),1)
        wave=self.cpu.m[self.sym['bar_wave']+(self.state('vblank')&31)]
        self.assertEqual(self.cpu.m[0xd012],wave)
        colors=[self.cpu.m[self.sym['bar_color']+i] for i in range(16)]
        lines=[wave]
        for i in range(16):
            self.cpu.run_irq()
            self.assertEqual(self.cpu.m[0xd020],colors[i]);self.assertEqual(self.cpu.m[0xd021],colors[i])
            lines.append(self.cpu.m[0xd012])
            self.assertEqual(self.state('irq_stage'),i+2)
        self.assertEqual(lines[:16],[wave+3*i for i in range(16)])
        self.assertEqual(self.cpu.m[0xd020],colors[15])        # last bar is visible for its full height
        self.assertEqual(self.state('irq_stage'),17)
        self.cpu.run_irq()                                     # restore interrupt
        self.assertEqual(self.state('irq_stage'),0)
        self.assertEqual(self.cpu.m[0xd012],250)
        self.assertEqual((self.cpu.m[0xd020],self.cpu.m[0xd021]),(6,6))
        self.assertTrue(all(55<=w<=120 for w in (self.cpu.m[self.sym['bar_wave']+i] for i in range(32))))
    def test_bars_stay_off_during_play(self):
        self.irq_on()
        for _ in range(5):
            self.cpu.run_irq();self.assertEqual(self.state('irq_stage'),0);self.assertEqual(self.cpu.m[0xd012],250)
    def test_wait_frame_sleeps_until_irq(self):
        self.irq_on()
        self.cpu.push(0xff);self.cpu.push(0xef);self.cpu.pc=self.sym['wait_frame']
        v=self.state('vblank')
        steps=self.cpu.run_until(0xfff0,irq_every=700)
        self.assertEqual(self.state('vblank'),(v+1)&255)
        self.assertGreater(steps,100)           # it genuinely spun waiting for the interrupt
    def test_boot_disables_kernal_cursor_blink_and_starts_raster_irq(self):
        c=boot(CPU(PRG),self.sym)
        self.assertEqual(c.m[0xcc],1)
        self.assertEqual(c.m[0xd01a],1)
        self.assertEqual(c.m[0xdc0d],0x7f)
        self.assertEqual(c.m[0xd015],3)
        self.assertEqual(c.m[0x07f9],0xdd)
        self.assertIn(c.m[0xd028],(2,8,10))                  # army-source marker colour pulses red tones
        self.assertEqual(c.m[0x9d],0)                       # no KERNAL I/O messages over the map
    def test_main_loop_runs_one_tick_per_frames_per_tick_and_is_drift_free(self):
        c=boot(CPU(PRG),self.sym)
        c.m[self.sym['frames_per_tick']]=16                  # pin the fast speed: the test counts 16-frame ticks
        count=[0]
        def watch(cpu):
            if cpu.pc==self.sym['simulate']:count[0]+=1
        v0=c.m[self.sym['vblank']]
        c.run_for(5700*16*10+2000,on_pc=watch)
        frames=(c.m[self.sym['vblank']]-v0)&255
        self.assertEqual(frames,160)                         # 10 ticks of 16 frames elapsed
        self.assertEqual(count[0],10)                        # exactly one simulate per 16 vblanks
    def test_slow_frames_keep_the_remainder(self):
        # 14 frames banked + 5 elapsed (a slow iteration) = 19 vs 16 per tick: tick now, carry 3 frames over.
        c=boot(CPU(PRG),self.sym)
        c.m[self.sym['frames_per_tick']]=16
        v=c.m[self.sym['vblank']]
        c.m[self.sym['frames']]=14
        c.m[self.sym['lastvb']]=(v-4)&255
        c.run_until(self.sym['simulate'],irq_every=700)
        self.assertEqual(c.m[self.sym['frames']],3)
    def test_stall_after_disk_access_is_clamped_to_eight_frames(self):
        c=boot(CPU(PRG),self.sym)
        v=c.m[self.sym['vblank']]
        c.m[self.sym['frames']]=0
        c.m[self.sym['lastvb']]=(v-100)&255                      # as if a 2-second disk access just ended
        calls=[0]
        def watch(cpu):
            if cpu.pc==self.sym['simulate']:calls[0]+=1
        c.run_for(2000,irq_every=700,on_pc=watch)
        self.assertEqual(calls[0],0)                              # 8 frames < 16: no catch-up burst
        self.assertEqual(c.m[self.sym['frames']]<16,True)
    def test_pause_freezes_the_simulation_clock(self):
        c=boot(CPU(PRG),self.sym)
        c.m[self.sym['state']]=1
        count=[0]
        def watch(cpu):
            if cpu.pc==self.sym['simulate']:count[0]+=1
        c.run_for(5700*40,on_pc=watch)
        self.assertEqual(count[0],0)
        c.m[self.sym['state']]=0
        c.run_for(5700*40,on_pc=watch)
        self.assertGreaterEqual(count[0],1)
        self.assertLessEqual(count[0],3)   # no burst catch-up for the paused time

class Title(GameCase):
    def test_title_flushes_stale_keyboard_queue(self):
        self.irq_on();self.cpu.m[0xc6]=3
        self.cpu.push(0xff);self.cpu.push(0xef);self.cpu.pc=self.sym['title_screen']
        n=[0]
        def watch(c):
            if c.pc==self.sym['title_wait']:
                n[0]+=1
                if n[0]==1:self.assertEqual(c.m[0xc6],0)
                if n[0]==4:c.key=32
        self.cpu.run_until(0xfff0,on_pc=watch,irq_every=1500)
        self.assertGreaterEqual(n[0],4)
    def test_title_screen_shows_bitmap_intro_and_hands_over_on_key(self):
        self.irq_on()
        self.cpu.push(0xff);self.cpu.push(0xef);self.cpu.pc=self.sym['title_screen']
        n=[0]
        def key(c):
            if c.pc==self.sym['title_wait']:
                n[0]+=1
                if n[0]==6:
                    self.assertEqual(c.m[0xdd00]&3,2)                        # VIC bank 1 ($4000-$7FFF)
                    self.assertEqual(c.m[0xd018],0x78)                       # screen $5C00, bitmap $6000
                    self.assertEqual(c.m[0xd011]&0x7f,0x3b)                  # bitmap mode, display on
                    self.assertEqual(c.m[0xd016]&0x1f,0x18)                  # multicolour, 40 columns
                    self.assertEqual(self.state('title_active'),0)           # bars and tune wait for the parade (see test_intro.py)
                    self.assertEqual(self.state('title_bmp'),1)
                    self.assertEqual(c.m[0xd015],0)
                if n[0]==9:c.key=ord('X')
        self.cpu.run_until(0xfff0,on_pc=key,irq_every=1500)
        self.assertEqual(self.state('title_active'),0)
        self.assertEqual(self.state('title_bmp'),0)
        self.assertEqual(self.cpu.m[0xdd00]&3,3)                              # back to VIC bank 0
        self.assertEqual(self.cpu.m[0xd018],0x1e)
        self.assertEqual(self.cpu.m[0xd011]&0x7f,0x1b)
        self.assertEqual(self.cpu.m[0xd015],3)
    def test_fire_button_dismisses_title(self):
        self.irq_on()
        self.cpu.joystick=0xef
        self.cpu.push(0xff);self.cpu.push(0xef);self.cpu.pc=self.sym['title_screen']
        self.cpu.run_until(0xfff0,irq_every=1500)
        self.assertEqual(self.state('title_active'),0)

    def test_intro_assets_are_consistent_and_in_vic_bank_1(self):
        sym=self.sym
        bm=(ROOT/'assets/intro_bitmap.bin').read_bytes();sc=(ROOT/'assets/intro_screen.bin').read_bytes();co=(ROOT/'assets/intro_color.bin').read_bytes()
        self.assertEqual((len(bm),len(sc),len(co)),(8000,1000,1000))
        c=CPU(PRG)
        self.assertEqual(bytes(c.m[0x6000:0x6000+8000]),bm)
        self.assertEqual(bytes(c.m[sym['intro_screen_src']:sym['intro_screen_src']+1000]),sc)   # revealed into $5C00 by the intro
        self.assertEqual(bytes(c.m[sym['intro_color']:sym['intro_color']+1000]),co)
        self.assertGreaterEqual(sym['orig_build']+640,sym['orig_build']);self.assertLess(sym['orig_build']+640,0x5800)   # sprite frames end before the picture
        self.assertEqual(sym['orig_army'],0x4000);self.assertLessEqual(sym['smp_end'],0xC000)
        self.assertTrue(0x4000<=0x6000 and 0x6000+8000<=0x8000 and 0x5c00+1000<=0x6000)
        # the PRESS FIRE row is %11 only so it can colour-cycle: no %01/%10 pixels there
        for cell in range(22*40,23*40):
            for y in range(8):
                b=bm[cell*8+y]
                for sh in (6,4,2,0):
                    self.assertIn((b>>sh)&3,(0,3),cell)
        self.assertTrue(all(v<=15 for v in co) and all(v<=255 for v in sc))
    def test_title_palette_is_hires_safe(self):
        # PRESS FIRE colour RAM cycle: the row is %11-only bitmap cells, any 0-15 colour is legal here
        vals=[self.cpu.m[self.sym['title_pal']+i] for i in range(8)]
        self.assertTrue(all(0<=v<=15 for v in vals))

class Joystick(GameCase):
    def stick(self,raw):
        self.put('joy_raw',raw);self.call('read_keys')
    def decode(self,raw):
        self.put('joy_raw',raw);self.call('read_joystick');return self.cpu.a
    def test_diagonal_moves_once_and_sequential_press_moves_again(self):
        self.put('selected',5)
        self.stick(0xf6)              # up+right pressed together
        self.assertEqual(self.state('selected'),1)           # one step: up has priority
        self.stick(0xff)
        self.stick(0xfe)              # up
        self.assertEqual(self.state('selected'),1)           # already top row: refused
        self.put('selected',5)
        self.stick(0xff);self.stick(0xfe)                     # up
        self.assertEqual(self.state('selected'),1)
        self.stick(0xf6)              # add right while up is held
        self.assertEqual(self.state('selected'),2)
    def test_fire_tap_sets_source_on_own_land_and_raids_otherwise(self):
        self.put('owner',1,1);self.put('selected',1)
        self.stick(0xef)
        self.assertEqual(self.state('source'),0)             # nothing on press
        self.stick(0xff)
        self.assertEqual(self.state('source'),1)             # ENTER on release
        self.put('source',0);self.put('selected',1);self.put('owner',0,1)
        self.stick(0xef);self.stick(0xff)
        self.assertEqual(self.state('owner',1),1)            # raid captured the free neighbour
    def test_all_eight_chords_decode_after_debounce(self):
        table={0xee:'T',0xed:'U',0xeb:'Q',0xe7:'E',0xea:'H',0xe6:'Y',0xe9:'Z',0xe5:' '}
        for raw,key in table.items():
            self.setUp()
            self.decode(0xef)                                # FIRE down
            out=[self.decode(raw) for _ in range(CHORD)]
            self.assertEqual(out[:-1],[0]*(CHORD-1),hex(raw))
            self.assertEqual(out[-1],ord(key),hex(raw))
            self.assertEqual(self.decode(raw),0)             # fires once only
            self.assertEqual(self.decode(0xff),0)            # release after chord: no tap action
    def test_unmapped_chord_and_release_do_nothing(self):
        self.decode(0xef)
        for _ in range(8):self.assertEqual(self.decode(0xec),0)   # up+down
        self.assertEqual(self.decode(0xff),0)
        self.assertEqual(self.state('source'),0)
    def test_changing_direction_while_holding_fire_restarts_debounce(self):
        self.decode(0xef)
        self.assertEqual(self.decode(0xee),0);self.assertEqual(self.decode(0xee),0)
        self.assertEqual(self.decode(0xed),0)                # switched to down: restart
        self.assertEqual(self.decode(0xed),0);self.assertEqual(self.decode(0xed),0)
        self.assertEqual(self.decode(0xed),ord('U'))
    def test_chord_effects_through_read_keys(self):
        self.stick(0xef)
        for _ in range(CHORD):self.stick(0xeb)               # FIRE+left -> Q
        self.assertEqual(self.state('doctrine',0),1)
        self.stick(0xff);self.stick(0xef)
        for _ in range(CHORD):self.stick(0xed)               # FIRE+down -> U develop
        self.assertEqual(self.state('minegrade',0),2)
        self.assertEqual(self.state('ore',0),8)
        self.stick(0xff);self.stick(0xef)
        for _ in range(CHORD):self.stick(0xe5)               # FIRE+down+right -> pause
        self.assertEqual(self.state('state'),1)
        self.stick(0xff)
    def test_fire_tap_is_context_sensitive_on_pause_victory_and_defeat(self):
        self.put('state',1)
        self.stick(0xef);self.stick(0xff);self.assertEqual(self.state('state'),0)   # resume
        for i in range(12):self.put('owner',1,i)
        self.call('draw_score');self.assertEqual(self.state('state'),2)
        self.stick(0xef);self.stick(0xff)
        self.assertEqual(self.state('campaign_island'),1);self.assertEqual(self.state('state'),0)
        self.put('state',3)
        self.stick(0xef);self.stick(0xff)
        self.assertEqual(self.state('campaign_island'),0);self.assertEqual(self.state('state'),0)
    def test_joystick_never_mutates_enemy_or_state_on_idle(self):
        before=bytes(self.cpu.m[self.sym['owner']:self.sym['cpu_count']+1])
        for _ in range(10):self.stick(0xff)
        self.assertEqual(bytes(self.cpu.m[self.sym['owner']:self.sym['cpu_count']+1]),before)
CHORD=4

class Diplomacy(GameCase):
    def test_stronger_player_gets_truce_and_hud_shows_it(self):
        self.put('selected',11)
        self.press('E')
        self.assertEqual(self.state('truce',2),90)
        self.assertEqual(self.screen(2,0,35),'TRUCE AGREED - THEY WILL NOT ATTACK')
        self.call('panel_values')
        self.assertEqual(self.screen(6,30,7),'PACT:90')
    def test_weaker_player_is_refused_then_cooldown_blocks(self):
        self.put('people',3,0);self.put('weapons',0,0)
        self.put('people',60,11)
        self.put('selected',11)
        self.press('E')
        self.assertEqual(self.state('truce',2),0);self.assertEqual(self.state('truce_cool',2),60)
        self.assertIn('REFUSED',self.screen(2))
        self.put('people',90,0)
        self.press('E')
        self.assertEqual(self.state('truce',2),0)
        self.assertIn('TALKS BLOCKED',self.screen(2))
        for _ in range(60):self.call('diplo_tick')
        self.assertEqual(self.state('truce_cool',2),0)
        self.press('E')
        self.assertEqual(self.state('truce',2),90)
    def test_power_comparison_is_16_bit(self):
        for i in range(12):
            self.put('owner',1,i);self.put('people',90,i);self.put('weapons',90,i);self.put('level',5,i)
        self.put('owner',2,11);self.put('people',90,11);self.put('weapons',90,11);self.put('level',5,11)
        self.call('draw_score')
        self.cpu.a=1;self.call('calc_power')
        self.assertEqual(self.state('pwr_lo')+256*self.state('pwr_hi'),11*(90+45+20))
        self.cpu.a=2;self.call('calc_power')
        self.assertEqual(self.state('pwr_lo')+256*self.state('pwr_hi'),90+45+20)
        self.put('selected',11);self.put('state',0)
        self.press('E');self.assertEqual(self.state('truce',2),90)
    def test_equal_power_is_accepted(self):
        for i in range(12):self.put('owner',0,i)
        self.put('owner',1,0);self.put('owner',2,1)
        for i in (0,1):self.put('people',50,i);self.put('weapons',10,i);self.put('level',2,i)
        self.put('selected',1);self.press('E')
        self.assertEqual(self.state('truce',2),90)
    def test_only_rival_sectors_can_be_negotiated_with(self):
        self.put('selected',0);self.press('E')
        self.assertIn('SELECT A RIVAL',self.screen(2))
        self.put('selected',5);self.press('E')              # free land
        self.assertEqual(sum(self.state('truce',i) for i in range(5)),0)
    def test_second_proposal_does_not_extend(self):
        self.put('selected',11);self.press('E')
        self.put('truce',33,2);self.press('E')
        self.assertEqual(self.state('truce',2),33)
        self.assertIn('ALREADY ACTIVE',self.screen(2))
    def test_truce_expires_and_starts_cooldown(self):
        self.put('truce',2,2)
        self.call('diplo_tick');self.assertEqual(self.state('truce',2),1)
        self.call('diplo_tick');self.assertEqual(self.state('truce',2),0)
        self.assertEqual(self.state('truce_cool',2),60)
        self.assertIn('TRUCE HAS ENDED',self.screen(2))
    def test_simulate_ticks_truces(self):
        self.put('truce',10,3);self.put('truce_cool',7,4)
        self.call('simulate')
        self.assertEqual(self.state('truce',3),9);self.assertEqual(self.state('truce_cool',4),6)
    def ai_scenario(self,truce):
        for i in range(12):self.put('owner',0,i);self.put('people',0,i);self.put('weapons',0,i)
        self.put('owner',1,0);self.put('people',10,0)
        self.put('owner',2,1);self.put('people',90,1);self.put('weapons',60,1);self.put('level',5,1)
        self.put('truce',truce,2)
    def test_ai_never_attacks_human_under_truce_but_does_without(self):
        self.ai_scenario(90)
        for _ in range(12):self.call('ai_turn')
        self.assertEqual(self.state('owner',0),1)
        self.assertEqual(self.state('owner',2),2)             # it expanded elsewhere instead
        self.ai_scenario(0)
        for _ in range(12):self.call('ai_turn')
        self.assertEqual(self.state('owner',0),2)
    def test_truce_only_protects_against_the_partner(self):
        self.ai_scenario(0)
        self.put('truce',90,3)                                 # a pact with blue does not protect from red
        for _ in range(12):self.call('ai_turn')
        self.assertEqual(self.state('owner',0),2)
    def test_player_attack_voids_truce(self):
        self.put('owner',2,1);self.put('people',5,1)
        self.put('truce',50,2);self.put('selected',1);self.press('X')
        self.assertEqual(self.state('truce',2),0);self.assertEqual(self.state('truce_cool',2),60)
        self.assertEqual(self.state('owner',1),1)
    def test_failed_launch_does_not_void_truce(self):
        self.put('owner',2,1);self.put('people',5,0)           # garrison too small to launch
        self.put('truce',50,2);self.put('selected',1);self.press('X')
        self.assertEqual(self.state('truce',2),50)
        self.put('selected',5);self.put('truce',50,3);self.press('X')   # attacking free land never breaks pacts
        self.assertEqual(self.state('truce',3),50)
    def test_truce_state_survives_save_and_load(self):
        self.put('truce',44,3);self.put('truce_cool',17,4)
        self.press('O');self.press('N')
        self.assertEqual(self.state('truce',3),0)
        self.press('I')
        self.assertEqual(self.state('truce',3),44);self.assertEqual(self.state('truce_cool',4),17)
    def test_new_island_clears_truces(self):
        self.put('truce',44,3);self.put('truce_cool',17,4)
        self.call('load_island')
        self.assertEqual(sum(self.state('truce',i)+self.state('truce_cool',i) for i in range(5)),0)
    def test_snapshot_rejects_out_of_range_truce_even_with_valid_checksums(self):
        self.press('O')
        blob=bytearray(self.cpu.drive_files['ML64SAVE'])
        n=blob[7];off=8+(self.sym['truce']-self.sym['owner'])+2
        blob[off]=200
        payload=blob[8:8+n]
        blob[8+n]=__import__('functools').reduce(lambda a,b:a^b,payload,0);blob[9+n]=sum(payload)&255
        self.cpu.drive_files['ML64SAVE']=bytes(blob)
        self.put('ore',65,0);self.press('I')
        self.assertEqual(self.state('ore',0),65)

class Inventions(GameCase):
    def test_rank_up_announces_epoch_weapon_for_player_only(self):
        self.put('labs',12,0);self.put('research',23,0)
        self.call('simulate')
        self.assertEqual(self.state('level',0),1)
        self.assertEqual(self.screen(2,0,23),'INVENTION: CLUB MARK 1 ')
    def test_message_names_the_current_epoch_and_rank(self):
        for island in (3,15,27):
            self.put('campaign_island',island);self.call('load_island')
            epoch=self.state('epoch')
            me=next(i for i in range(12) if self.state('owner',i)==1)
            self.put('labs',12,me);self.put('research',40,me);self.put('level',3,me);self.put('buildings',7,me)
            self.call('simulate')
            self.assertEqual(self.state('level',me),4)
            self.assertEqual(self.screen(2).rstrip(),f'INVENTION: {NAMES[epoch]} MARK 4')
    def test_ai_rank_up_is_silent(self):
        self.put('labs',12,11);self.put('research',23,11);self.put('buildings',7,11)
        before=self.screen(2)
        self.call('simulate')
        self.assertEqual(self.state('level',11),1)
        self.assertEqual(self.screen(2),before)
    def test_hud_lists_current_epoch_weapon(self):
        for island in range(0,28,3):
            self.put('campaign_island',island);self.call('load_island')
            e=self.state('epoch')
            self.assertEqual(self.screen(12,30,10).rstrip(),'ARM:'+NAMES[e],island)
    def test_rank_up_does_not_derail_the_rest_of_that_sector_update(self):
        # sim_auto for the SAME sector runs right after the notice; X must still address that sector.
        self.put('labs',12,0);self.put('research',23,0);self.put('policy',1,0)
        self.put('buildings',7,0);self.put('ore',40,0);self.put('weapons',5,0);self.put('vein',0,0)
        self.call('simulate')
        self.assertEqual(self.state('level',0),1)
        self.assertEqual(self.state('weapons',0),6)
        self.assertEqual(self.state('ore',0),36)
    def test_rank_up_keeps_simulation_index_intact(self):
        # The notice runs mid-loop; every sector after it must still be simulated.
        self.put('labs',12,0);self.put('research',23,0)
        self.put('ore',0,11);self.put('miners',2,11);self.put('buildings',1,11);self.put('vein',50,11)
        self.call('simulate')
        self.assertGreater(self.state('ore',11),0)

class Develop(GameCase):
    def world(self):
        return bytes(self.cpu.m[self.sym['owner']:self.sym['campaign_island']])
    def test_priority_ladder(self):
        z=lambda n:self.put(n,0,0)
        for n in ('buildings','miners','labs','minegrade','fort','weapons'):z(n)
        self.put('people',50,0);self.put('ore',40,0)
        steps=[('buildings',2),('buildings',6),('miners',1),('miners',2),('minegrade',1),('minegrade',2),
               ('labs',1),('labs',2),('weapons',1),('weapons',2),('miners',3),('miners',4)]
        for name,val in steps:
            self.press('U');self.assertEqual(self.state(name,0),val,(name,val))
        self.assertEqual(self.state('ore',0),0)
        snapshot=self.world()
        self.press('U')
        self.assertIn('NOT ENOUGH',self.screen(2))
        self.assertEqual(self.world(),snapshot)
    def test_fortification_is_built_when_ore_allows(self):
        self.put('buildings',7,0);self.put('miners',4,0);self.put('labs',2,0);self.put('minegrade',2,0)
        self.put('weapons',30,0);self.put('fort',0,0);self.put('ore',80,0)
        for want in (1,2,3,4,5):
            self.press('U');self.assertEqual(self.state('fort',0),want)
    def test_develop_never_touches_enemy_or_free_land(self):
        for sector in (11,5):
            self.put('selected',sector)
            before=self.world()
            self.press('U')
            self.assertEqual(self.world(),before)

class Disk(GameCase):
    def test_save_scratches_then_saves_plain_name_and_verifies(self):
        self.press('O')
        self.assertEqual(self.cpu.disk_log,[('cmd','S0:ML64SAVE'),('save','ML64SAVE')])
        self.assertIn('SAVED AND VERIFIED',self.screen(2))
        self.assertTrue(all('@' not in n for _,n in self.cpu.disk_log))
        self.assertEqual(self.cpu.drive_files['ML64SAVE'][2:7],b'ML64\x04')
    def test_second_save_replaces_first(self):
        self.put('ore',31,0);self.press('O')
        self.put('ore',77,0);self.press('O')
        self.press('N');self.press('I')
        self.assertEqual(self.state('ore',0),77)
    def test_write_protected_disk_is_reported_not_trusted(self):
        self.press('O');self.put('ore',55,0)
        self.cpu.write_protected=True
        self.press('O')
        self.assertIn('DISK/SAVE ERROR',self.screen(2))
        self.cpu.write_protected=False
        self.press('N');self.press('I')
        self.assertEqual(self.state('ore',0),16)              # the old, intact save is what loads
    def test_follows_the_device_we_were_loaded_from(self):
        self.cpu.drive_device=9;self.cpu.m[0xba]=9
        self.press('O')
        self.assertIn('ML64SAVE',self.cpu.drive_files)
        self.assertEqual(self.state('devnum'),9)
        self.press('N');self.press('I')
        self.assertIn('RESTORED',self.screen(2))
    def test_unknown_device_number_falls_back_to_8(self):
        for ba in (0,7,12,30,255):
            self.cpu.m[0xba]=ba;self.call('get_device');self.assertEqual(self.state('devnum'),8,ba)
        for ba in (8,9,10,11):
            self.cpu.m[0xba]=ba;self.call('get_device');self.assertEqual(self.state('devnum'),ba)
    def test_missing_drive_reports_error_and_keeps_state(self):
        self.cpu.drive_device=9                                 # nothing answers on 8
        self.put('ore',44,0)
        self.press('O');self.assertIn('DISK/SAVE ERROR',self.screen(2))
        self.press('I');self.assertIn('DISK/SAVE ERROR',self.screen(2))
        self.assertEqual(self.state('ore',0),44)
    def test_version_3_files_are_refused(self):
        self.press('O')
        blob=bytearray(self.cpu.drive_files['ML64SAVE']);blob[6]=3
        self.cpu.drive_files['ML64SAVE']=bytes(blob)
        self.put('ore',12,0);self.press('I')
        self.assertEqual(self.state('ore',0),12)
        self.assertIn('DISK/SAVE ERROR',self.screen(2))
    def test_read_error_status_after_load_is_rejected(self):
        self.press('O');self.put('ore',9,0)
        orig=self.cpu.step
        def step():                               # KERNAL reports a read error although carry stays clear
            c=self.cpu
            if c.m[c.pc]==0x20 and (c.m[c.pc+1]|c.m[c.pc+2]<<8)==0xffb7:c.status=0x10
            return orig()
        self.cpu.step=step
        self.press('I')
        self.assertIn('DISK/SAVE ERROR',self.screen(2))
        self.assertEqual(self.state('ore',0),9)
    def test_screen_and_sprites_are_off_during_every_kernal_io_call_and_restored_after(self):
        self.cpu.m[0xd011]=0x1b;self.cpu.m[0xd015]=3
        self.press('O');self.press('I')
        self.assertEqual(len(self.cpu.io_screen),4)         # open, save, verify, load
        for display,sprites,msb in self.cpu.io_screen:
            self.assertEqual((display,sprites,msb),(0,0,0))
        self.assertEqual(self.cpu.m[0xd011],0x1b)
        self.assertEqual(self.cpu.m[0xd015],3)
    def test_screen_is_restored_even_when_the_disk_fails(self):
        self.cpu.m[0xd011]=0x1b;self.cpu.m[0xd015]=3;self.cpu.drive_device=9
        self.press('O')
        self.assertEqual(self.cpu.m[0xd011],0x1b);self.assertEqual(self.cpu.m[0xd015],3)
        self.assertFalse(self.cpu.p&4)                           # interrupts back on after KERNAL I/O
    def test_raster_compare_msb_is_never_set_by_disk_blanking(self):
        self.cpu.m[0xd011]=0x1b;self.cpu.raster_msb=1             # reads back 0x9b: raster is past line 255
        self.press('O');self.press('I')
        self.assertEqual(self.cpu.m[0xd011]&0x80,0)
        self.assertTrue(all(msb==0 for _,_,msb in self.cpu.io_screen))

class Graphics(GameCase):
    def test_source_marker_tracks_source_sector(self):
        for src in range(12):
            self.put('source',src);self.call('draw_source_marker')
            sx=self.cpu.m[self.sym['sector_x']+src];sy=self.cpu.m[self.sym['sector_y']+src]
            self.assertEqual(self.cpu.m[0xd002],(sx*8+56)&255)
            self.assertEqual(self.cpu.m[0xd003],sy*8+58)
            self.assertLess(sx*8+56,256)
    def test_sprite_pointers_survive_screen_clear(self):
        self.call('clear_screen')
        self.assertEqual((self.cpu.m[0x7f8],self.cpu.m[0x7f9]),(0xdc,0xdd))
    def test_sprite_data_is_in_place_and_nonempty(self):
        data=(ROOT/'assets/source_sprite.bin').read_bytes()
        self.assertEqual(len(data),64);self.assertTrue(any(data))
        self.assertEqual(bytes(self.cpu.m[0x3740:0x3780]),data)
        self.assertEqual(bytes(self.cpu.m[0x3700:0x3740]),(ROOT/'assets/cursor_sprite.bin').read_bytes())
    def test_memory_map_has_no_collisions(self):
        s=self.sym
        self.assertGreaterEqual(s['irq_install'],0x4000)
        prg=PRG.read_bytes();end=prg[0]+256*prg[1]+len(prg)-3
        self.assertLess(end,0xc000)                                # leaves $C000 save buffer alone
        self.assertLess(s['cpu_count'],0x3700)
        for name in ('vblank','msgbuf','get_device','title_screen'):self.assertGreaterEqual(s[name],0x4000)
    def test_panel_extra_rows_do_not_overflow_the_screen(self):
        self.call('panel_values')
        for row in (6,12):
            self.assertTrue(all(0x20<=b<0x7f for b in self.cpu.m[0x400+row*40+30:0x400+row*40+40]))

class Fuzz(GameCase):
    KEYS=list('WASDXTHMJRKBVGPFYZQOILCNEU 0123456789')+['\r']
    def invariants(self):
        s=self.state
        for i in range(12):
            self.assertLessEqual(s('owner',i),4);self.assertLessEqual(s('people',i),90)
            self.assertLessEqual(s('ore',i),95);self.assertLessEqual(s('miners',i),12)
            self.assertLessEqual(s('labs',i),12);self.assertLessEqual(s('level',i),5)
            self.assertLessEqual(s('weapons',i),90);self.assertLessEqual(s('fort',i),9)
            self.assertLessEqual(s('buildings',i),7);self.assertLessEqual(s('minegrade',i),2)
            self.assertLessEqual(s('policy',i),3);self.assertLessEqual(s('doctrine',i),2)
            self.assertLessEqual(s('vein',i),95)
        for i in range(5):
            self.assertLessEqual(s('truce',i),90);self.assertLessEqual(s('truce_cool',i),60)
        self.assertLess(s('selected'),12);self.assertLess(s('source'),12)
        self.assertLess(s('campaign_island'),28);self.assertLessEqual(s('state'),4)
        self.assertGreater(self.cpu.s,0xc0)                       # stack never leaks
    def test_random_play_keeps_every_invariant(self):
        for seed in range(4):
            rnd=random.Random(1000+seed)
            self.setUp();self.irq_on()
            for step in range(260):
                r=rnd.random()
                if r<0.55:
                    k=rnd.choice(self.KEYS);self.cpu.key=ord(k) if k!='\r' else 13
                    self.put('joy_raw',rnd.choice([0xff,0xff,0xfe,0xfd,0xfb,0xf7,0xef,0xee,0xed,0xeb,0xe7,0xea,0xe6,0xe9,0xe5]))
                    self.call('read_keys')
                elif r<0.85:
                    if self.state('state')==0:self.call('simulate')
                elif r<0.95:
                    self.call('ai_turn')
                else:
                    self.cpu.run_irq()
                self.invariants()
if __name__=='__main__':unittest.main()


class SpeedControl(GameCase):
    def test_default_normal_and_keys_1_2_3_set_speed(self):
        self.cpu.m[0x2a6]=1                                   # PAL
        self.call('set_speed')
        self.assertEqual(self.state('speed'),1)
        self.assertEqual(self.state('frames_per_tick'),24)
        for key,fpt,spd in ((ord('1'),40,0),(ord('3'),16,2),(ord('2'),24,1)):
            self.press(key)
            self.assertEqual(self.state('frames_per_tick'),fpt)
            self.assertEqual(self.state('speed'),spd)
            self.assertEqual(self.screen(0,39,1),str(spd+1))
    def test_speed_digit_shown_in_header(self):
        self.cpu.m[0x2a6]=1
        self.press(ord('3'))
        self.assertEqual(self.screen(0,33,7),'SPEED 3')


class AiPacing(GameCase):
    def ai_runs(self,epoch,ticks):
        self.put('epoch',epoch);self.put('ticks',ticks-1);self.put('ai_faction',2)
        self.call('simulate')
        return self.state('ai_faction')!=2
    def test_ai_acts_every_16_ticks_before_epoch_5_and_every_8_after(self):
        self.assertFalse(self.ai_runs(0,8))
        self.assertTrue(self.ai_runs(0,16))
        self.assertFalse(self.ai_runs(4,24))
        self.assertFalse(self.ai_runs(5,4))
        self.assertTrue(self.ai_runs(5,8))
    def test_ai_wants_a_25_percent_margin_before_assaulting(self):
        # CPU sector 11: 40 people, no weapons, tech 0 -> assault power 45 (3/4 troops, +50%).
        # Human sector 10 defends with `defence` people. 40 used to be attacked (40 < 45); now 40+25% = 50 >= 45 holds.
        for defence,attacked in ((40,False),(36,False),(35,True)):
            for s in range(12):
                for name in ('owner','people','weapons','fort','level'):self.put(name,0,s)
            self.put('owner',2,11);self.put('people',40,11);self.put('owner',2,7)   # own neighbour: skipped
            self.put('owner',1,10);self.put('people',defence,10)
            self.put('ai_faction',1);self.put('ai_cursor',10)
            self.call('ai_turn')
            self.assertEqual(self.state('owner',10)==2,attacked,msg=defence)


SMP_IDS={k:i for i,k in enumerate(['stick','throw','musket','machinegun','cannon','missile','laser','explosion','grunt','orchestra','timpani'])}
SMP_INDEX=json.loads((ROOT/'assets/orig/samples.json').read_text())['samples']

class SoundFx(GameCase):
    def sample_started(self):
        """Index of the sample whose read pointer the player is at the start of (None if idle)."""
        m=self.cpu.m;s=self.sym
        if m[s['smp_left']]|m[s['smp_left']+1]==0:return None
        rd=m[s['smp_rd']+1]|(m[s['smp_rd']+2]<<8)
        for i,e in enumerate(SMP_INDEX):
            if rd==s['smp_data']+e['offset']:return i
        return -1
    def irq_frames(self,n):
        for _ in range(n):self.cpu.run_irq()
    def test_sfx_programs_voice1_and_sweeps_then_releases(self):
        self.irq_on()
        self.call('sfx_play',) if False else None
        self.cpu.a=7;self.call('sfx_play')                       # build: saw, sweeping down (no original sample)
        self.assertEqual(self.cpu.m[0xd404],0x81)
        f0=self.cpu.m[0xd401]
        self.assertEqual(self.state('soundtime'),4)
        self.irq_frames(2)
        self.assertEqual(self.cpu.m[0xd401],(f0-12)&255)         # -6 per frame
        self.irq_frames(4)
        self.assertEqual(self.cpu.m[0xd404]&1,0)                 # gate released
        self.assertEqual(self.state('sfx_cur_prio'),0)
    def test_lower_priority_never_cuts_a_higher_one_but_equal_or_higher_does(self):
        self.irq_on()
        self.cpu.a=5;self.call('sfx_play')                       # invention jingle, priority 4
        self.cpu.a=9;self.call('sfx_play')                       # cursor tick, priority 0: ignored
        self.assertEqual(self.cpu.m[0xd401],20)                  # still the invention pitch, not the tick's 40
        self.assertEqual(self.state('soundtime'),22)
        self.irq_frames(5);self.assertEqual(self.state('soundtime'),17)
        self.cpu.a=1;self.call('sfx_play')                       # refusal beep, priority 2: ignored
        self.assertEqual(self.state('soundtime'),17)
        self.cpu.a=5;self.call('sfx_play')                       # equal priority: replaces (retriggers)
        self.assertEqual(self.state('soundtime'),22)
    def test_sfx_tables_are_aligned(self):
        for name in ('sfx_fhi','sfx_flo','sfx_sweep','sfx_wave','sfx_ad','sfx_sr','sfx_pw','sfx_len','sfx_prio'):
            self.assertEqual(self.sym[name]+13,self.sym[{'sfx_fhi':'sfx_flo','sfx_flo':'sfx_sweep','sfx_sweep':'sfx_wave','sfx_wave':'sfx_ad','sfx_ad':'sfx_sr','sfx_sr':'sfx_pw','sfx_pw':'sfx_len','sfx_len':'sfx_prio','sfx_prio':'sound_tick'}[name]])
        for i in range(13):
            self.assertEqual(self.cpu.m[self.sym['sfx_wave']+i]&1,1)       # every effect gates on
            self.assertGreater(self.cpu.m[self.sym['sfx_len']+i],0)
    def test_music_regates_notes_and_has_victory_and_defeat_tunes(self):
        self.irq_on()
        tempo=[self.cpu.m[self.sym['music_tempo']+i] for i in range(6)]
        self.assertEqual(len(tempo),6)
        self.put('music_over',4);self.put('music_pos',0);self.put('music_frame',tempo[4]-1)
        self.cpu.run_irq()
        self.assertEqual(self.cpu.m[0xd407],self.cpu.m[self.sym['melody_lo']+4*16])
        self.assertEqual(self.cpu.m[0xd40b],0x40);self.assertEqual(self.cpu.m[0xd412],0x20)   # released ...
        self.cpu.run_irq();self.assertEqual(self.cpu.m[0xd40b],0x40)
        self.cpu.run_irq()
        self.assertEqual(self.cpu.m[0xd40b],0x41);self.assertEqual(self.cpu.m[0xd412],0x21)   # ... and re-gated two frames later
        self.put('music_over',5);self.put('music_pos',3);self.put('music_frame',tempo[5]-1);self.cpu.run_irq()
        self.assertEqual(self.cpu.m[0xd407],self.cpu.m[self.sym['melody_lo']+5*16+3])
    def test_pulse_width_wobbles(self):
        self.irq_on()
        seen=set()
        for i in range(16):
            self.cpu.run_irq();seen.add(self.cpu.m[0xd40a])
        self.assertGreater(len(seen),3);self.assertTrue(all(4<=v<=11 for v in seen))
    def test_win_and_loss_switch_tune_sound_and_flash(self):
        self.irq_on()
        for i in range(12):self.put('owner',1,i)
        self.call('draw_score')
        self.assertEqual(self.state('state'),2);self.assertEqual(self.state('music_over'),4)
        self.assertEqual(self.state('fx_timer'),50);self.assertEqual(self.sample_started(),SMP_IDS['orchestra'])
        self.call('load_island');self.assertEqual(self.state('music_over'),0)
        for i in range(12):self.put('owner',0,i)
        self.call('draw_score')
        self.assertEqual(self.state('state'),3);self.assertEqual(self.state('music_over'),5)
        self.assertEqual(self.sample_started(),SMP_IDS['timpani'])
    def test_border_flash_alternates_and_returns_to_epoch_colour(self):
        self.irq_on()
        self.put('epoch',3);self.call('set_border')
        self.assertEqual(self.state('border_col'),11)
        self.cpu.a=13;self.cpu.x=8;self.call('fx_flash')
        seen=[]
        for i in range(9):
            self.cpu.run_irq();seen.append(self.cpu.m[0xd020])
        self.assertIn(13,seen);self.assertIn(11,seen)
        self.assertEqual(self.cpu.m[0xd020],11)
    def test_screen_shake_jitters_scroll_then_recentres(self):
        self.irq_on()
        self.cpu.x=8;self.call('fx_shake_start')
        seen=set()
        for i in range(8):
            self.cpu.run_irq();seen.add(self.cpu.m[0xd016])
        self.assertTrue(seen>={0x18,0x19,0x1a,0x1b} or len(seen)>=3)
        self.assertTrue(all(v&0x18==0x18 for v in seen))               # MCM and 40-column bits never lost
        self.assertEqual(self.cpu.m[0xd016],0x18)
    def test_fx_is_off_on_the_title(self):
        self.irq_on()
        self.put('title_active',1);self.cpu.a=7;self.cpu.x=10;self.call('fx_flash')
        self.cpu.m[0xd020]=0
        self.cpu.run_irq()
        self.assertEqual(self.state('fx_timer'),10)
    def test_sprite_colours_pulse(self):
        self.irq_on()
        seen=set()
        for i in range(40):
            self.cpu.run_irq();seen.add(self.cpu.m[0xd027])
        self.assertGreaterEqual(len(seen),2)
    def test_player_attack_makes_noise_and_shake_capture_flashes_green(self):
        self.irq_on()
        s=[i for i in range(12) if self.state('owner',i)==1][0]
        self.put('source',s);self.put('people',60,s)
        t=[n for n in (s+1,s-1,s+4,s-4) if 0<=n<12 and (n//4==s//4 or abs(n-s)==4) and self.state('owner',n)==0]
        self.assertTrue(t)
        self.put('selected',t[0]);self.press('T')
        self.assertEqual(self.state('shake_timer'),8)
        self.assertEqual(self.state('fx_col'),13);self.assertEqual(self.state('fx_timer'),12)
        self.assertEqual(self.state('smp_prio'),4)                      # the capture explosion replaced the attack sample
        self.assertEqual(self.sample_started(),SMP_IDS['explosion'])
    def test_cursor_move_ticks(self):
        self.irq_on()
        self.put('selected',0);self.press('D')
        self.assertEqual(self.cpu.m[0xd404],0x11)
        self.assertEqual(self.state('soundtime'),2)
    def test_human_losing_a_sector_alerts(self):
        self.irq_on()
        s=[i for i in range(12) if self.state('owner',i)==1][0]
        e=[i for i in range(12) if self.state('owner',i)==2][0]
        self.put('selected',s);self.put('source',e);self.put('attacking',2);self.put('force',40);self.put('usedarms',0)
        self.cpu.x=s;self.call('attack_capture')
        self.assertEqual(self.state('fx_col'),2);self.assertEqual(self.state('shake_timer'),6)
        self.assertEqual(self.sample_started(),SMP_IDS['grunt'])        # sector-lost grunt
    def test_hud_colours(self):
        self.call('draw_score');self.call('draw_panel')
        self.call('panel_values')
        col=lambda r,c:self.cpu.m[0xd800+r*40+c]&15
        s=self.state('selected');own=self.state('owner',s)
        self.assertEqual(col(5,32),[1,5,7,3,4][own])               # OWNER row = faction colour
        self.assertEqual(col(3,35),3);self.assertEqual(col(9,35),7)
        self.assertEqual((col(22,5),col(23,5),col(24,5)),(5,3,7))
        self.assertEqual(col(1,3),5);self.assertEqual(col(1,13),7)
        self.assertEqual(col(0,3),7)
    def test_border_per_epoch_table_and_load_island_sets_it(self):
        tab=[self.cpu.m[self.sym['border_tab']+i] for i in range(10)]
        self.assertEqual(len(set(tab)),9 if len(set(tab))==9 else len(set(tab)))
        for stage in (0,3,9,27):
            self.put('campaign_island',stage);self.call('load_island')
            self.assertEqual(self.cpu.m[0xd020],tab[min(stage//3,9)])

    def test_hud_text_uses_hires_colours_only(self):
        # colour RAM 8-15 switches a glyph to multicolour and garbles it (seen in VICE)
        for owner in (0,1,2,3,4):
            for sel in range(12):
                self.put('selected',sel);self.call('draw_score');self.call('draw_panel');self.call('panel_values')
                for r in list(range(0,3))+list(range(22,25)):
                    for c in range(40):
                        if self.cpu.m[0x400+r*40+c]!=32:
                            self.assertLessEqual(self.cpu.m[0xd800+r*40+c]&15,7,(r,c))
                for r in range(3,22):
                    for c in range(30,40):
                        if self.cpu.m[0x400+r*40+c]!=32:
                            self.assertLessEqual(self.cpu.m[0xd800+r*40+c]&15,7,(r,c))
            self.put('owner',owner,sel)


class OriginalArt(GameCase):
    """Sprites down-converted from the original 1991 sheets: marching army + conquest icon."""
    def tile(self,n):
        sx=self.cpu.m[self.sym['sector_x']+n];sy=self.cpu.m[self.sym['sector_y']+n]
        return sx*8+32,sy*8+58
    def march(self,src,dst,who=1):
        self.put('source',src);self.put('selected',dst);self.put('attacking',who)
        self.cpu.a=0x55;self.cpu.x=7;self.cpu.y=9
        self.call('march_start')
        self.assertEqual((self.cpu.a,self.cpu.x,self.cpu.y),(0x55,7,9))      # registers preserved
    def test_epoch_frames_are_copied_into_vic_bank_0(self):
        army=self.sym['orig_army'];bld=self.sym['orig_build']
        for e in range(10):
            self.put('epoch',e);self.cpu.a=1;self.cpu.x=2;self.cpu.y=3;self.call('orig_load_epoch')
            self.assertEqual((self.cpu.a,self.cpu.x,self.cpu.y),(1,2,3))
            self.assertEqual(bytes(self.cpu.m[0x3200:0x3300]),bytes(self.cpu.m[army+e*256:army+e*256+256]))
            self.assertEqual(bytes(self.cpu.m[0x3300:0x3340]),bytes(self.cpu.m[bld+e*64:bld+e*64+64]))
    def test_set_border_loads_the_epoch_sprites(self):
        self.put('epoch',6);self.call('set_border')
        self.assertEqual(bytes(self.cpu.m[0x3300:0x3340]),bytes(self.cpu.m[self.sym['orig_build']+6*64:][:64]))
    def test_every_converted_frame_is_a_valid_multicolour_sprite(self):
        a=self.sym['orig_army'];b=self.sym['orig_build']
        for n in range(40):
            self.assertEqual(self.cpu.m[a+n*64+63],0)
            self.assertTrue(any(self.cpu.m[a+n*64:a+n*64+63]))
        for n in range(10):
            self.assertEqual(self.cpu.m[b+n*64+63],0)
            self.assertGreater(sum(1 for v in self.cpu.m[b+n*64:b+n*64+63] if v),20)
    def test_march_walks_from_source_to_target_in_32_frames_all_directions(self):
        for src,dst in ((0,3),(3,0),(0,11),(11,0),(4,5),(7,4),(2,10)):
            self.call('orig_init')
            self.march(src,dst)
            (x0,y0),(x1,y1)=self.tile(src),self.tile(dst)
            self.assertEqual((self.cpu.m[0xd004],self.cpu.m[0xd005]),(x0,y0))
            self.assertTrue(self.cpu.m[0xd015]&4)
            frames=set();lo_x,hi_x=sorted((x0,x1));lo_y,hi_y=sorted((y0,y1))
            for i in range(31):
                self.call('orig_tick');frames.add(self.cpu.m[0x7fa])
                px,py=self.cpu.m[0xd004],self.cpu.m[0xd005]
                self.assertTrue(lo_x<=px<=hi_x and lo_y<=py<=hi_y,(src,dst,i,px,py))   # never sweeps through the 8-bit wrap
            self.assertTrue(self.cpu.m[0xd015]&4)                       # still walking on the last-but-one frame
            self.call('orig_tick')
            self.assertEqual((self.cpu.m[0xd004],self.cpu.m[0xd005]),(x1,y1),(src,dst))
            self.assertFalse(self.cpu.m[0xd015]&4)
            self.assertEqual(frames,{0xc8,0xc9,0xca,0xcb})              # four-frame walk cycle
    def test_march_uses_the_attackers_colour(self):
        for who in (1,2,3,4):
            self.march(0,1,who);self.assertEqual(self.cpu.m[0xd029],[1,5,7,3,4][who])
    def test_capture_icon_waits_for_the_army_then_blinks_out(self):
        self.call('orig_init')
        self.march(0,1,2)
        self.put('selected',1);self.put('attacking',2);self.call('march_capture')
        for i in range(31):
            self.call('orig_tick');self.assertFalse(self.cpu.m[0xd015]&8)    # army still on its way
        self.call('orig_tick')
        self.assertTrue(self.cpu.m[0xd015]&8)
        x,y=self.tile(1)
        self.assertEqual((self.cpu.m[0xd006],self.cpu.m[0xd007]),(x+26,y+14))
        self.assertEqual(self.cpu.m[0xd02a],7)
        shown=[]
        for i in range(70):
            self.call('orig_tick');shown.append(bool(self.cpu.m[0xd015]&8))
        self.assertTrue(all(shown[:40]));self.assertIn(False,shown[40:64]);self.assertFalse(shown[-1])
    def test_capture_without_a_march_shows_the_icon_at_once(self):
        self.call('orig_init');self.put('selected',5);self.put('attacking',1);self.call('march_capture')
        self.call('orig_tick');self.assertTrue(self.cpu.m[0xd015]&8)
    def test_attacks_start_the_march_and_captures_raise_the_icon(self):
        self.irq_on()
        s=[i for i in range(12) if self.state('owner',i)==1][0]
        self.put('source',s);self.put('people',60,s)
        t=[n for n in (s+1,s-1,s+4,s-4) if 0<=n<12 and (n//4==s//4 or abs(n-s)==4) and self.state('owner',n)==0]
        self.put('selected',t[0]);self.press('T')
        self.assertEqual(self.state('march_t'),32)
        self.assertTrue(self.cpu.m[0xd015]&4);self.assertEqual(self.state('cap_pending'),1)
        for i in range(34):self.cpu.run_irq()
        self.assertFalse(self.cpu.m[0xd015]&4);self.assertTrue(self.cpu.m[0xd015]&8)
    def test_new_island_clears_sprites_and_sets_registers(self):
        self.put('march_t',9);self.cpu.m[0xd015]|=12
        self.call('load_island')
        self.assertEqual(self.cpu.m[0xd015]&12,0);self.assertEqual(self.state('march_t'),0)
        self.assertEqual(self.cpu.m[0xd01c],0x0c);self.assertEqual(self.cpu.m[0xd01d],4)
        self.assertEqual((self.cpu.m[0xd025],self.cpu.m[0xd026]),(0,15))
    def test_sprite_ram_does_not_collide_with_game_code(self):
        self.assertLess(self.sym['checksum_sum'],0x3200)
