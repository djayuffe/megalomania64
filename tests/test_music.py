"""Synthetic tests for Amiga-sector recovery, MOD interpretation and the SID driver."""
import struct
from common import *
from recover_amiga import payload, module_info
from make_music import score
from scene_format import encode


def synthetic_mod():
    data=bytearray(1084+1024+2)
    data[:4]=b'TEST';data[42:44]=b'\0\1';data[45]=64;data[48:50]=b'\0\1'
    data[950]=1;data[1080:1084]=b'M.K.'
    # Row 0, channel 1: instrument 1, C at period 428, F07 (seven ticks/row).
    data[1088:1092]=bytes((1,0xac,0x1f,7))
    # Row 3: break to the next order after this row, preserving current timing.
    data[1084+3*16+4:1084+3*16+8]=bytes((0,0,0x0d,0))
    return bytes(data)


class AmigaFormats(unittest.TestCase):
    def test_custom_sector_payload_omits_only_the_two_byte_footer(self):
        raw=bytes(range(255))*4
        physical=raw[:510]+b'\x01\x04'+raw[510:]+b'\x01\x05'
        self.assertEqual(payload(physical),raw)
        with self.assertRaises(ValueError):payload(physical[:-1])

    def test_module_parser_checks_size_and_instruments(self):
        data=synthetic_mod();info=module_info(data)
        self.assertEqual((info['orders'],info['patterns'],info['size']),(1,1,len(data)))
        with self.assertRaises(ValueError):module_info(data[:-1])
        bad=bytearray(data);bad[1084]=0x20
        with self.assertRaises(ValueError):module_info(bad)

    def test_score_preserves_speed_change_and_pattern_break(self):
        stream,info=score(synthetic_mod())
        self.assertEqual(info['frames'],28)
        self.assertEqual(stream[0],28)
        self.assertEqual(stream[1]&63,25)
        self.assertEqual(stream[-4:],bytes(4))

    def test_score_rejects_unsupported_commands(self):
        data=bytearray(synthetic_mod());data[1090]=0x11
        with self.assertRaises(ValueError):score(data)


class OriginalScore(GameCase):
    def bank(self,duration=100):
        bank=bytearray(256)
        for note in range(64):
            bank[note*2:note*2+2]=bytes((note,note+1))
            bank[128+note*2:130+note*2]=bytes((note+2,note+3))
        bank+=struct.pack('<HH',0xc504,0xc50c)
        bank+=bytes((duration,25,0,0,0,0,0,0))
        bank+=bytes((duration,0,26,0,0,0,0,0))
        return b'MLM1'+len(bank).to_bytes(2,'little')+bank

    def load(self,data=None):
        self.cpu.drive_files['MUSIC']=data or self.bank()
        self.call('music_load')
        self.cpu.m[0x02a6]=1

    def test_score_bank_loads_and_control_data_has_no_sprite_overlap(self):
        self.load();self.assertEqual(self.state('mu_ready'),1)
        self.assertLessEqual(self.sym['mu_data_end'],0x3400)
        self.assertLessEqual(self.sym['control_data_end'],0x3700)
        self.assertEqual(self.cpu.channels,{})

    def test_title_and_game_use_their_own_original_score(self):
        self.load();self.put('title_active',1);self.call('music_tick')
        self.assertEqual(self.cpu.m[0xd400:0xd402],bytes((25,26)))
        self.assertEqual(self.cpu.m[0xd404],0x10) # note off for one frame before gate on
        self.call('music_tick');self.assertEqual(self.cpu.m[0xd404],0x11)
        self.put('title_active',0);self.call('music_tick')
        self.assertEqual(self.cpu.m[0xd407:0xd409],bytes((26,27)))
        self.assertEqual(self.state('mu_mode'),0)

    def test_ntsc_uses_its_frequency_table_and_fifty_hz_timebase(self):
        self.load();self.cpu.m[0x02a6]=0
        for _ in range(60):self.call('music_tick')
        self.assertEqual(self.state('mu_wait'),51)
        self.assertEqual(self.cpu.m[0xd407:0xd409],bytes((28,29)))

    def test_tonal_effect_keeps_voice_one_until_it_finishes(self):
        self.load();self.put('title_active',1);self.call('music_tick')
        self.put('soundtime',4);self.cpu.m[0xd400:0xd402]=b'\xaa\xbb';self.cpu.m[0xd404]=0x81
        self.call('music_tick');self.assertEqual(self.cpu.m[0xd400:0xd402],b'\xaa\xbb')
        self.assertEqual(self.cpu.m[0xd404],0x81)
        self.put('soundtime',0);self.call('music_tick')
        self.assertEqual(self.cpu.m[0xd400:0xd402],bytes((25,26)))
        self.assertEqual(self.cpu.m[0xd404],0x11)

    def test_voice_digi_pauses_the_original_score(self):
        self.load();self.call('music_tick');wait=self.state('mu_wait')
        self.cpu.a=0;self.call('sample_play');self.call('sound_tick')
        self.assertEqual(self.state('mu_wait'),wait)
        self.call('sample_stop');self.call('sound_tick');self.assertEqual(self.state('mu_wait'),wait-1)

    def test_bad_length_or_pointer_cannot_enable_the_bank(self):
        for at,value in [(5,0x10),(6+257,0xd0)]:
            data=bytearray(self.bank());data[at]=value;self.load(data)
            self.assertEqual(self.state('mu_ready'),0)

    def test_truncated_bank_and_runtime_overrun_disable_playback(self):
        self.load(self.bank()[:-1]);self.assertEqual(self.state('mu_ready'),0)
        self.load();end=self.state('mu_end')|(self.state('mu_end',1)<<8)
        self.cpu.m[self.sym['mu_fetch']+1:self.sym['mu_fetch']+3]=end.to_bytes(2,'little')
        self.call('mu_read');self.assertTrue(self.cpu.flag(1));self.assertEqual(self.state('mu_ready'),0)

    def test_skip_carry_survives_loading_music_before_game_start(self):
        blank=encode(bytes(8000),bytes(1000),bytes(1000),frames=4)
        self.cpu.drive_files={'SCENE01':blank,'SCENE02':blank,'MUSIC':self.bank()}
        self.cpu.drive_files['TITLE']=encode((ROOT/'assets/intro_bitmap.bin').read_bytes(),
            (ROOT/'assets/intro_screen.bin').read_bytes(),(ROOT/'assets/intro_color.bin').read_bytes(),multicolor=True)
        hit=[]
        def skip(cpu):
            if cpu.pc==self.sym['ic_displayed']:cpu.key=32
            if cpu.pc==self.sym['title_wait']:hit.append('unexpected native title')
        self.cpu.m[0x02a6]=1;self.cpu.pc=self.sym['start']
        self.cpu.run_until(self.sym['main_loop'],max_steps=4000000,on_pc=skip)
        self.assertEqual(hit,[]);self.assertEqual(self.state('mu_ready'),1)
