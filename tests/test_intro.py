"""v4.4 tests: original-sample player (NMI, 4-bit digi) and the multi-scene intro."""
import json, unittest
from common import *

SAMPLES=json.loads((ROOT/'assets/orig/samples.json').read_text())['samples']
BLOB=(ROOT/'assets/orig/samples.bin').read_bytes()
NAMES=['stick','throw','musket','machinegun','cannon','missile','laser','explosion','grunt','orchestra','timpani']


def nibbles(i):
    e=SAMPLES[i];out=[]
    for k in range(e['nibbles']):
        b=BLOB[e['offset']+k//2]
        out.append(b>>4 if k%2==0 else b&15)
    return out


class SamplePlayer(GameCase):
    def play(self,i,pal=True):
        self.cpu.m[0x02a6]=1 if pal else 0
        self.cpu.a=i;self.call('sample_play')

    def test_sample_bank_matches_the_index(self):
        self.assertEqual([e['key'] for e in SAMPLES][:3],['stick','throw','musket'])
        self.assertEqual(len(SAMPLES),11)
        end=0
        for e in SAMPLES:
            self.assertEqual(e['offset'],end);end+=e['nibbles']//2
            self.assertEqual(e['nibbles']%2,0)
        self.assertEqual(end,len(BLOB))
        self.assertEqual(bytes(self.cpu.m[self.sym['smp_data']:self.sym['smp_data']+len(BLOB)]),BLOB)
        self.assertLessEqual(self.sym['smp_end'],0xC000)
        for i,e in enumerate(SAMPLES):
            self.assertEqual(self.cpu.m[self.sym['smp_off_lo']+i]|(self.cpu.m[self.sym['smp_off_hi']+i]<<8),self.sym['smp_data']+e['offset'])
            self.assertEqual(self.cpu.m[self.sym['smp_len_lo']+i]|(self.cpu.m[self.sym['smp_len_hi']+i]<<8),e['nibbles'])

    def test_every_sample_streams_its_nibbles_high_first_to_the_sid_volume(self):
        for i,e in enumerate(SAMPLES):
            self.play(i)
            want=nibbles(i);got=[]
            for _ in range(e['nibbles']):
                self.call('sample_step');got.append(self.cpu.m[0xd418])
                if len(got)<e['nibbles']:self.assertEqual(self.cpu.m[0xdd0e],0x11,NAMES[i])   # timer still running
            self.assertEqual(got[:-1],want[:-1],NAMES[i])                                   # last write is the stop's volume restore
            self.assertEqual(self.cpu.m[0xd418],0x0f)
            self.assertEqual(self.state('smp_left')|self.state('smp_left',1),0)
            self.assertEqual(self.cpu.m[0xdd0e],0)                                          # timer stopped
            self.assertEqual(self.cpu.m[0xdd0d],0x7f)                                       # NMI source off

    def test_playback_rate_pal_and_ntsc(self):
        self.play(0,True)
        self.assertEqual((self.cpu.m[0xdd04],self.cpu.m[0xdd05]),(196,0))
        self.assertEqual((self.cpu.m[0xdd0e],self.cpu.m[0xdd0d]),(0x11,0x81))
        self.play(0,False)
        self.assertEqual((self.cpu.m[0xdd04],self.cpu.m[0xdd05]),(203,0))
        self.assertAlmostEqual(985248/197,5000,delta=5);self.assertAlmostEqual(1022727/204,5000,delta=15)

    def test_sid_voices_are_muted_while_a_sample_plays_and_restored_after(self):
        for r in (0xd406,0xd40d,0xd414):self.cpu.m[r]=0x55
        for r in (0xd404,0xd40b,0xd412):self.cpu.m[r]=0x41                          # all three voices sounding
        self.play(3)
        self.assertEqual((self.cpu.m[0xd406],self.cpu.m[0xd40d],self.cpu.m[0xd414]),(0,0,0xf0))      # sustain 0, fast release
        self.assertEqual((self.cpu.m[0xd404]&1,self.cpu.m[0xd40b]&1,self.cpu.m[0xd412]),(0,0,0x49)) # gates off
        self.call('sample_stop')
        self.assertEqual((self.cpu.m[0xd406],self.cpu.m[0xd40d],self.cpu.m[0xd414]),(0xa5,0xa6,0xa6))
        self.assertEqual(self.cpu.m[0xd418],0x0f)

    def test_stop_preserves_registers_and_is_safe_when_idle(self):
        self.cpu.a=0x42;self.cpu.x=0x17;self.cpu.y=0x99
        self.call('sample_stop')
        self.assertEqual((self.cpu.a,self.cpu.x,self.cpu.y),(0x42,0x17,0x99))
        self.assertEqual(self.state('smp_left'),0)

    def test_8580_detection_boosts_three_dc_sources_and_stop_removes_every_test_bit(self):
        self.cpu.m[0xd41b]=0x80;self.call('sample_init')
        self.assertEqual(self.state('sid_8580'),1)
        self.play(1)
        self.assertEqual([self.cpu.m[a] for a in (0xd404,0xd40b,0xd412)],[0x49]*3)
        self.assertEqual([self.cpu.m[a] for a in (0xd406,0xd40d,0xd414)],[0xf0]*3)
        self.call('sample_stop')
        self.assertEqual([self.cpu.m[a]&9 for a in (0xd404,0xd40b,0xd412)],[0]*3)
        self.cpu.m[0xd41b]=0x3f;self.call('sample_init')
        self.assertEqual(self.state('sid_8580'),0)

    def test_new_sample_replaces_the_running_one(self):
        self.play(4);self.call('sample_step');self.call('sample_step')
        self.play(2)
        self.assertEqual(self.state('smp_left')|(self.state('smp_left',1)<<8),SAMPLES[2]['nibbles'])
        self.assertEqual(self.state('smp_half'),0)
        self.call('sample_step')
        self.assertEqual(self.cpu.m[0xd418],nibbles(2)[0])

    def test_boot_installs_the_nmi_vector_and_idle_volume(self):
        self.call('irq_install')
        self.assertEqual(self.cpu.m[0x0318]|(self.cpu.m[0x0319]<<8),self.sym['nmi_entry'])
        self.assertEqual(self.cpu.m[0x01]&7,6)                       # BASIC out, KERNAL and I/O in
        self.assertEqual(self.cpu.m[0xdd0d],0x7f)

    def nmi(self,cia_flag):
        """Run one NMI through nmi_entry: 6510 pushes PC and P, the KERNAL vector jumps to the handler."""
        c=self.cpu
        regs=(c.a,c.x,c.y);sp=c.s
        c.m[0xdd0d]=0x81 if cia_flag else 0x00
        c.push(0xff);c.push(0xf0);c.push(c.p)
        c.pc=self.sym['nmi_entry'];n=0
        while c.pc!=0xfff0:
            c.step();n+=1
            self.assertLess(n,500)
        self.assertEqual((c.a,c.x,c.y),regs);self.assertEqual(c.s,sp)
        return n

    def test_nested_nmi_cannot_underflow_the_last_sample_counter(self):
        self.play(1);self.put('smp_left',1);self.put('smp_left',0,1)
        c=self.cpu;c.m[0xdd0d]=0x81
        c.push(0xff);c.push(0xf0);c.push(c.p);c.pc=self.sym['nmi_entry']
        for _ in range(200):
            if c.pc==self.sym['sm_out']:break
            c.step()
        else:self.fail('outer NMI did not reach the sample write')
        resume=c.pc
        c.push(resume>>8);c.push(resume&255);c.push(c.p);c.pc=self.sym['nmi_entry']
        for _ in range(300):
            if c.pc==resume:break
            c.step()
        else:self.fail('nested NMI did not return')
        for _ in range(500):
            if c.pc==0xfff0:break
            c.step()
        else:self.fail('outer NMI did not return')
        self.assertEqual(self.state('smp_left')|(self.state('smp_left',1)<<8),0)
        self.assertEqual(self.state('nmi_busy'),0)
        self.assertEqual(c.m[0xdd0e],0)

    def test_nested_nmi_during_banked_read_acknowledges_the_real_cia(self):
        self.play(1);self.cpu.m[1]=0x34;self.put('nmi_busy',1)
        self.cpu.ram_io[0xd0d]=0;before=self.cpu.cia2_reads
        left=self.state('smp_left')|(self.state('smp_left',1)<<8)
        self.nmi(True)
        self.assertGreater(self.cpu.cia2_reads,before)
        self.assertEqual(self.cpu.m[1],0x34)
        self.assertEqual(self.state('smp_left')|(self.state('smp_left',1)<<8),left)

    def test_nmi_entry_steps_the_player_and_keeps_registers(self):
        self.play(1)
        self.cpu.a=0x31;self.cpu.x=0x42;self.cpu.y=0x53
        n=self.nmi(True)
        self.assertEqual(self.cpu.m[0xd418],nibbles(1)[0])
        self.assertLess(n,120)                                       # leaves well over half the 197-cycle slot to the game
        self.nmi(True)
        self.assertEqual(self.cpu.m[0xd418],nibbles(1)[1])

    def test_nmi_without_cia_flag_is_ignored(self):
        self.play(1)
        self.cpu.m[0xd418]=0x0c
        self.nmi(False)                                              # RESTORE key
        self.assertEqual(self.cpu.m[0xd418],0x0c)
        self.assertEqual(self.state('smp_left')|(self.state('smp_left',1)<<8),SAMPLES[1]['nibbles'])

    def test_step_on_idle_player_just_stops(self):
        self.call('sample_stop');self.cpu.m[0xd418]=0
        self.call('sample_step')
        self.assertEqual(self.cpu.m[0xd418],0x0f)


class SampleEvents(GameCase):
    def started(self):
        m=self.cpu.m;s=self.sym
        if m[s['smp_left']]|m[s['smp_left']+1]==0:return None
        rd=m[s['smp_rd']+1]|(m[s['smp_rd']+2]<<8)
        for i,e in enumerate(SAMPLES):
            if rd==s['smp_data']+e['offset']:return i
        return -1

    def sfx(self,i):
        self.cpu.a=i;self.call('sfx_play')

    def test_attack_uses_the_weapon_of_the_epoch(self):
        want=[0,0,1,1,2,2,3,4,5,6]       # stick, stick, throw, throw, musket, musket, machine gun, cannon, missile, laser
        for epoch,smp in enumerate(want):
            self.call('sample_stop');self.put('smp_prio',0)
            self.put('epoch',epoch);self.sfx(2)
            self.assertEqual(self.started(),smp,epoch)

    def test_event_samples_and_silent_events(self):
        for sfx,smp in ((3,7),(4,8),(10,9),(11,10),(12,2)):
            self.call('sample_stop');self.put('smp_prio',0)
            self.sfx(sfx);self.assertEqual(self.started(),smp,sfx)
        self.call('sample_stop')
        for sfx in (0,1,5,6,7,8,9):                                  # these stay on the SID voice
            self.sfx(sfx);self.assertIsNone(self.started(),sfx)

    def test_sid_effect_replaced_by_sample_and_blocked_while_it_plays(self):
        self.cpu.m[0xd404]=0
        self.sfx(3)                                                  # capture: sample, no SID gate
        self.assertEqual(self.cpu.m[0xd404]&1,0);self.assertEqual(self.state('soundtime'),0)
        self.sfx(5)                                                  # invention jingle must not gate the muted voice
        self.assertEqual(self.state('soundtime'),0);self.assertEqual(self.cpu.m[0xd404]&1,0)
        self.call('sample_stop')
        self.sfx(5);self.assertEqual(self.state('soundtime'),22)

    def test_lower_priority_sample_does_not_cut_a_higher_one(self):
        self.sfx(11)                                                 # defeat timpani, priority 6
        self.sfx(3)                                                  # capture, priority 4: ignored
        self.assertEqual(self.started(),10)
        self.sfx(10)                                                 # victory, priority 6: replaces
        self.assertEqual(self.started(),9)

    def test_sequencer_waits_while_a_sample_plays(self):
        self.call('irq_install')
        self.put('music_pos',3);self.put('music_frame',0)
        self.sfx(3)
        for _ in range(5):self.cpu.run_irq()
        self.assertEqual((self.state('music_pos'),self.state('music_frame')),(3,0))
        self.call('sample_stop')
        for _ in range(3):self.cpu.run_irq()
        self.assertGreater(self.state('music_frame')+self.state('music_pos'),3)

    def test_disk_access_stops_the_sample(self):
        self.sfx(3);self.assertIsNotNone(self.started())
        self.call('disk_begin')
        self.assertEqual(self.state('smp_left')|self.state('smp_left',1),0)
        self.assertEqual(self.cpu.m[0xdd0d],0x7f)


class Intro(GameCase):
    def run_intro(self,frames,watch=None,key_at=None,joy_at=None):
        """Run title_screen from its entry; `watch(frame_no)` is called at every title_wait pass."""
        self.irq_on()
        c=self.cpu
        c.push(0xff);c.push(0xef);c.pc=self.sym['title_screen']
        n=[0]
        def hook(cpu):
            if cpu.pc==self.sym['title_wait']:
                n[0]+=1
                if watch:watch(n[0])
                if key_at and n[0]==key_at:cpu.key=ord('X')
                if joy_at and n[0]==joy_at:cpu.joystick=0xef
                if n[0]>=frames:raise StopIteration
        try:c.run_until(0xfff0,on_pc=hook,irq_every=1500,max_steps=4000000)
        except StopIteration:pass
        return n[0]

    def test_starts_black_and_reveals_from_the_middle_row_outwards(self):
        pic_col=(ROOT/'assets/intro_color.bin').read_bytes();pic_scr=(ROOT/'assets/intro_screen.bin').read_bytes()
        seen={}
        def watch(n):
            if n in (1,2,6,10,22,54):seen[n]=(bytes(self.cpu.m[0xd800:0xd800+1000]),bytes(self.cpu.m[0x5c00:0x5c00+1000]),self.state('it'))
        self.run_intro(54,watch)
        col,scr,_=seen[1]                          # pass 1 = before the first step: everything black
        self.assertEqual(col,bytes(1000));self.assertEqual(scr,bytes(1000))
        col,scr,_=seen[2]                          # step 0 opens the middle row only
        for r in range(25):
            if r!=12:self.assertEqual(col[r*40:r*40+40],bytes(40),r);self.assertEqual(scr[r*40:r*40+40],bytes(40),r)
        self.assertEqual(col[12*40:13*40],pic_col[12*40:13*40]);self.assertEqual(scr[12*40:13*40],pic_scr[12*40:13*40])
        for n,k in ((6,1),(10,2),(22,5)):           # step k opens rows 12-k..12+k
            col,scr,_=seen[n]
            for r in range(25):
                shown=abs(r-12)<=k
                if shown:self.assertEqual(col[r*40:r*40+40],pic_col[r*40:r*40+40],(n,r))
                if shown:self.assertEqual(scr[r*40:r*40+40],pic_scr[r*40:r*40+40],(n,r))
                else:
                    self.assertEqual(scr[r*40:r*40+40],bytes(40),(n,r));self.assertEqual(col[r*40:r*40+40],bytes(40),(n,r))
        col,scr,it=seen[54]
        self.assertEqual(it,52)
        self.assertEqual(scr[:1000],pic_scr)
        self.assertEqual(col[:22*40],pic_col[:22*40]);self.assertEqual(col[23*40:],pic_col[23*40:])   # row 22 is colour-cycling by now

    def test_intro_opens_with_the_original_orchestra_hit(self):
        got=[]
        def watch(n):
            if n==1:got.append((self.state('smp_left')|(self.state('smp_left',1)<<8),self.cpu.m[self.sym['smp_rd']+1]|(self.cpu.m[self.sym['smp_rd']+2]<<8)))
        self.run_intro(1,watch)
        self.assertEqual(got[0][0]>0,True)
        self.assertEqual(got[0][1],self.sym['smp_data']+SAMPLES[9]['offset'])

    def test_vic_bank_and_bitmap_setup(self):
        res={}
        def watch(n):
            if n==3:
                m=self.cpu.m
                res.update(bank=m[0xdd00]&3,d018=m[0xd018],d011=m[0xd011]&0x7f,d016=m[0xd016]&0x1f,bmp=self.state('title_bmp'),
                           mc=m[0xd01c],xe=(m[0xd017],m[0xd01d]),pri=m[0xd01b],mc1=m[0xd025],mc2=m[0xd026],hold=self.state('music_hold'),act=self.state('title_active'))
        self.run_intro(3,watch)
        self.assertEqual((res['bank'],res['d018'],res['d011'],res['d016']),(2,0x78,0x3b,0x18))
        self.assertEqual((res['bmp'],res['hold'],res['act']),(1,1,0))     # music held, bars off until the parade is over
        self.assertEqual((res['mc'],res['xe'],res['pri'],res['mc1'],res['mc2']),(0xff,(0,0),0,0,15))

    def test_parade_walks_in_lands_on_slots_and_fires_the_epoch_weapon(self):
        fxlo=[self.cpu.m[self.sym['ip_fxlo']+i] for i in range(8)];fxhi=[self.cpu.m[self.sym['ip_fxhi']+i] for i in range(8)]
        slots=[fxlo[i]|(fxhi[i]<<8) for i in range(8)]
        self.assertEqual(slots,sorted(slots));self.assertTrue(all(24<=x<=320 for x in slots))
        self.assertTrue(all(slots[i+1]-slots[i]>=24 for i in range(7)))    # 24 px sprites never overlap
        prev={'x':[0]*8,'arr':0,'st':[0]*8}
        log=[]
        weapon=[0,0,1,1,2,2,3,4]
        def watch(n):
            m=self.cpu.m;s=self.sym
            xs=[m[s['ip_xlo']+k]|(m[s['ip_xhi']+k]<<8) for k in range(8)]
            sts=[m[s['ip_st']+k] for k in range(8)]
            en=m[0xd015];msb=m[0xd010]
            for k in range(8):
                self.assertGreaterEqual(xs[k],prev['x'][k],(n,k))             # only ever walks right
                self.assertLessEqual(xs[k],slots[k],(n,k))
                self.assertLessEqual(xs[k]-prev['x'][k],3)
                self.assertEqual((en>>k)&1,1 if sts[k] else 0,(n,k))          # sprite on from its first step
                if sts[k]:
                    self.assertEqual(m[0xd000+2*k]|(((msb>>k)&1)<<8),xs[k],(n,k))
                    self.assertEqual(m[0xd001+2*k],200)
                    ptr=m[0x5ff8+k];self.assertEqual(ptr>>2,k);self.assertLess(ptr,40)
                    self.assertEqual(m[0xd027+k]&15,m[s['ip_col']+k])
                self.assertEqual(sts[k]==2,xs[k]==slots[k],(n,k))
            arr=m[s['ip_arrived']]
            if arr>prev['arr']:
                self.assertEqual(arr,prev['arr']+1)
                k=[j for j in range(8) if sts[j]==2 and prev['st'][j]!=2]
                self.assertEqual(len(k),1)
                rd=m[s['smp_rd']+1]|(m[s['smp_rd']+2]<<8)
                self.assertEqual(rd,s['smp_data']+SAMPLES[weapon[k[0]]]['offset'],k)
                log.append((n,k[0]))
            prev['x']=xs;prev['arr']=arr;prev['st']=sts
        self.run_intro(420,watch)
        self.assertEqual([k for _,k in log],list(range(8)))                   # one soldier per epoch, in order
        gaps=[log[i+1][0]-log[i][0] for i in range(7)]
        self.assertTrue(all(g>=30 for g in gaps),gaps)                         # >= 0.6 s apart: every weapon sample is heard
        self.assertTrue(all(d>=24 for d in [log[i+1][0]-log[i][0] for i in range(7)]) )
        self.assertEqual(self.state('title_active'),1);self.assertEqual(self.state('music_hold'),0)
        self.assertEqual(self.cpu.m[0xd015],255)

    def test_msb_set_only_for_sprites_past_x_255(self):
        def watch(n):pass
        self.run_intro(420,watch)
        self.assertEqual(self.cpu.m[0xd010],0xc0)                             # soldiers 6 and 7 stand right of x=255

    def test_music_and_bars_wait_for_the_end_of_the_parade(self):
        flags=[]
        def watch(n):
            flags.append((self.state('music_hold'),self.state('title_active'),self.state('ip_arrived')))
        self.run_intro(420,watch)
        for hold,act,arr in flags:
            if arr<8:self.assertEqual((hold,act),(1,0))
            else:self.assertEqual((hold,act),(0,1))
        self.assertEqual(flags[-1][2],8)

    def test_sequencer_is_held_during_the_reveal_even_without_a_sample(self):
        self.run_intro(30)
        self.call('sample_stop')                                  # the model never finishes a sample by itself
        self.assertEqual(self.state('music_hold'),1)
        self.cpu.m[0xd407]=0
        v0=self.state('vblank');n=0
        while (self.state('vblank')-v0)&255<30:
            self.cpu.run_irq();n+=1;self.assertLess(n,400)
        self.assertEqual((self.state('music_frame'),self.state('music_pos')),(0,0))
        self.assertEqual(self.cpu.m[0xd407],0)                    # no game tune over the intro

    def test_title_tune_plays_once_the_parade_is_done(self):
        self.run_intro(420)
        self.assertEqual(self.state('music_hold'),0)
        self.cpu.m[0xd407]=0
        self.call('sample_stop')
        self.put('music_frame',0)
        v0=self.state('vblank');n=0
        while (self.state('vblank')-v0)&255<12:               # bar-stage IRQs do not count as frames
            self.cpu.run_irq();n+=1;self.assertLess(n,400)
        self.assertNotEqual(self.cpu.m[0xd407],0)

    def test_press_fire_row_cycles_only_after_it_is_revealed(self):
        rows=[]
        def watch(n):
            if n in (20,40,60,64,68):rows.append(bytes(self.cpu.m[0xd800+22*40:0xd800+23*40]))
        self.run_intro(70,watch)
        self.assertEqual(rows[0],bytes(40));self.assertEqual(rows[1],bytes(40))   # still black while unrevealed
        self.assertGreater(len(set(rows[2])),3)
        self.assertNotEqual(rows[2],rows[4])                                      # animates

    def test_key_skips_at_any_point_and_restores_everything(self):
        for frame in (3,30,60,200,400):
            self.setUp()
            m=self.cpu.m
            m[0xd027]=7;m[0xd028]=10;m[0xd01c]=0x0c;m[0xd017]=4;m[0xd01d]=4;m[0xd025]=5;m[0xd026]=13
            m[0xd02a]=3;m[0xd010]=1;m[0xd000]=77;m[0xd001]=88;m[0xd002]=99;m[0xd01b]=0
            self.run_intro(999,key_at=frame)
            self.assertEqual(self.state('title_active'),0,frame);self.assertEqual(self.state('title_bmp'),0)
            self.assertEqual(self.state('music_hold'),0)
            self.assertEqual(self.state('smp_left')|self.state('smp_left',1),0)      # sample cut off
            self.assertEqual(m[0xdd0e],0)
            self.assertEqual((m[0xdd00]&3,m[0xd018],m[0xd011]&0x7f,m[0xd020],m[0xd021],m[0xd015]),(3,0x1e,0x1b,6,6,3),frame)
            self.assertEqual((m[0xd027],m[0xd028],m[0xd01c],m[0xd017],m[0xd01d],m[0xd025],m[0xd026],m[0xd02a],m[0xd010]),(7,10,0x0c,4,4,5,13,3,1),frame)
            self.assertEqual((m[0xd000],m[0xd001],m[0xd002]),(77,88,99),frame)

    def test_fire_skips_the_intro_too(self):
        self.run_intro(999,joy_at=20)
        self.assertEqual(self.state('title_active'),0)
        self.assertEqual(self.cpu.m[0xd015],3)

    def test_intro_source_data_and_layout(self):
        s=self.sym
        self.assertEqual(bytes(self.cpu.m[s['intro_screen_src']:s['intro_screen_src']+1000]),(ROOT/'assets/intro_screen.bin').read_bytes())
        self.assertGreaterEqual(s['intro_screen_src'],s['orig_build']+640)
        self.assertLessEqual(s['intro_screen_src']+1000,s['intro_color'])
        self.assertEqual(s['intro_screen_src'],0x4d00)
        self.assertLess(0x5c00+1000,0x5ff8)                                       # picture screen RAM never touches the sprite pointers
