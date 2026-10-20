"""Regressions for full effects, SID state recovery and perceptual bitmap colours."""
from common import *
from scene_format import pack
try:
    from PIL import Image
    from vic_bitmap import convert
except ImportError:
    Image=None
import json
from orig_convert import C64


class FullEffects(GameCase):
    def test_mixed_story_irq_keeps_text_hires_and_counts_one_frame(self):
        self.irq_on();self.put('ic_active',1);self.put('ic_visible_mode',2)
        before=self.state('vblank');self.cpu.run_irq()
        self.assertEqual(self.cpu.m[0xd016],0x18)
        self.assertEqual(self.cpu.m[0xd012],210)
        self.assertEqual(self.state('irq_stage'),18)
        self.cpu.run_irq()
        self.assertEqual(self.cpu.m[0xd016],8)
        self.assertEqual(self.cpu.m[0xd012],250)
        self.assertEqual(self.state('vblank'),(before+1)&255)
        self.assertEqual(self.state('irq_stage'),0)

    def load(self,data=None):
        self.raw=bytes((i*19+7)&255 for i in range(12072))
        self.cpu.drive_files['EFFECTS']=data if data is not None else b'MLF1'+pack(self.raw[:9000])+pack(self.raw[9000:])
        self.cpu.call(self.sym['effects_load'],max_ops=2000000)

    def test_story_display_holds_without_serial_reads_and_clears_split_on_exit(self):
        from scene_format import encode
        self.cpu.drive_files['SCENE01']=encode(bytes(8000),bytes(1000),bytes(1000),multicolor=2,frames=8)
        self.cpu.drive_files['TITLE']=encode((ROOT/'assets/intro_bitmap.bin').read_bytes(),
            (ROOT/'assets/intro_screen.bin').read_bytes(),(ROOT/'assets/intro_color.bin').read_bytes(),multicolor=True)
        self.irq_on();observed=[]
        self.cpu.pc=self.sym['intro_sequence'];self.cpu.push(0xff);self.cpu.push(0xef)
        def observe(c):
            if c.pc==self.sym['ic_story_hold']:
                self.assertEqual(self.state('ld_opened'),0);observed.append('hold')
            if c.pc==self.sym['ic_load'] and self.state('ic_visible_mode')==2:
                self.assertEqual(c.m[0xd011]&0x10,0)
        self.cpu.run_until(0xfff0,max_steps=2000000,on_pc=observe)
        self.assertTrue(observed);self.assertEqual(self.state('ic_visible_mode'),0)
        self.assertEqual(self.state('irq_stage'),0)

    def test_complete_bank_loads_without_touching_sid_registers(self):
        self.cpu.m[1]=0x36;self.cpu.m[0xd418]=15
        self.load()
        self.assertEqual(self.state('fx_ready'),1);self.assertEqual(self.state('fx_valid'),1)
        self.assertEqual(self.cpu.m[1],0x36)
        self.assertEqual(bytes(self.cpu.m[self.sym['smp_data']:self.sym['smp_end']]),self.raw[:9000])
        self.assertEqual(bytes(self.cpu.ram_io[0x400:]),self.raw[9000:])
        self.assertEqual(self.cpu.m[0xd418],15)

    def test_a_full_clip_crosses_the_two_regions_and_finishes_at_its_exact_end(self):
        self.load();index=json.loads((ROOT/'assets/orig/samples.json').read_text())['samples']
        effect=next(i for i,e in enumerate(index) if e['full_offset']<9000<e['full_offset']+e['full_nibbles']//2)
        e=index[effect];self.cpu.m[1]=0x36;self.cpu.a=effect;self.call('sample_play')
        actual=[]
        for _ in range(e['full_nibbles']-1):
            self.call('sample_step');actual.append(self.cpu.m[0xd418])
        expected=[(self.raw[e['full_offset']+i//2]>>(0 if i&1 else 4))&15 for i in range(e['full_nibbles']-1)]
        self.assertEqual(bytes(actual),bytes(expected))
        self.call('sample_step')
        self.assertEqual(self.state('smp_left')|self.state('smp_left',1)<<8,0)
        self.assertEqual(self.cpu.m[1],0x36)

    def test_truncated_optional_bank_disables_partial_samples_and_uses_sid_fallback(self):
        self.load(b'MLF1'+pack(bytes(9000))+b'\xff')
        self.assertEqual(self.state('fx_ready'),0);self.assertEqual(self.state('fx_valid'),0)
        self.cpu.a=2;self.call('sfx_play')
        self.assertGreater(self.state('soundtime'),0)
        self.assertEqual(self.state('smp_left')|self.state('smp_left',1)<<8,0)

    def test_missing_extension_keeps_the_builtin_effects(self):
        self.call('effects_load');self.assertEqual(self.state('fx_valid'),1)
        self.assertEqual(self.state('fx_ready'),0)
        self.cpu.a=0;self.call('sample_play');self.assertGreater(self.state('smp_left'),0)

    def test_capture_keeps_explosion_before_the_spoken_reaction(self):
        self.put('sp_ready',1);self.cpu.a=3;self.call('sfx_play')
        self.assertEqual(self.state('smp_speech'),0)
        self.assertEqual(self.state('sp_queue'),0)
        self.put('smp_left',0);self.put('smp_left',0,1);self.call('sample_finished')
        self.assertEqual(self.state('smp_speech'),1)
        self.assertEqual(self.state('sp_id'),0)


@unittest.skipIf(Image is None,"colour conversion requires Pillow and NumPy")
class ColourConversion(unittest.TestCase):
    def test_grey_text_does_not_turn_brown(self):
        im=Image.new('RGB',(320,200),(40,40,40))
        *_,shown=convert(im,True)
        self.assertTrue(set(shown.getdata()) <= {C64[i] for i in (0,1,11,12,15)})

    def test_hires_pair_preserves_small_bright_letters(self):
        im=Image.new('RGB',(320,200),C64[0])
        im.putpixel((0,0),C64[1])
        bitmap,screen,color,shown=convert(im)
        self.assertEqual(shown.getpixel((0,0)),C64[1])
        self.assertEqual(shown.getpixel((1,0)),C64[0])
        self.assertEqual(bitmap[0],0x80)
        self.assertEqual(screen[0],0x10)

    def test_multicolour_uses_all_four_pixel_codes_and_correct_register_nibbles(self):
        im=Image.new('RGB',(320,200),C64[0])
        for y in range(8):
            for x,c in enumerate([0,2,5,7]):
                im.paste(C64[c],(x*2,y,x*2+2,y+1))
        bitmap,screen,color,shown=convert(im,multicolor=True)
        self.assertEqual(set((bitmap[0]>>shift)&3 for shift in [6,4,2,0]),{0,1,2,3})
        self.assertEqual(set([0,screen[0]>>4,screen[0]&15,color[0]]),{0,2,5,7})
        self.assertEqual([shown.getpixel((x*2,0))for x in range(4)],[C64[c]for c in [0,2,5,7]])
