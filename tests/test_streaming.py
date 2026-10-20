"""Disk codec and 6502 streaming tests using synthetic assets, never original data."""
import struct
import tempfile
from pathlib import Path
from common import *
from scene_format import pack, unpack, encode, decode, encode_credit
from make_d64 import make_image, read_files, OFFSET
from lzhuf import decompress, Huffman, TREE, ROOT as HUFF_ROOT


def literal_stream(data):
    # Walk the adaptive tree upwards to emit literal codewords (no LZ matches).
    tree, bits = Huffman(), []
    for value in data:
        node = tree.parent[value + TREE]
        code = []
        while True:
            code.append(node & 1)
            node = tree.parent[node]
            if node == HUFF_ROOT:
                break
        bits.extend(reversed(code));tree.update(value)
    bits.extend([0] * ((-len(bits)) % 8))
    return struct.pack('<I', len(data)) + bytes(sum(bits[i+j] << (7-j) for j in range(8)) for i in range(0,len(bits),8))


class Codecs(unittest.TestCase):
    def test_lzhuf_literals_and_tree_reconstruction(self):
        raw = bytes(range(256)) * 150
        self.assertEqual(decompress(literal_stream(raw)), raw)

    def test_lzhuf_common_iff_prefix_fixture(self):
        # All original compressed IFF streams share these first four packed bytes.
        self.assertEqual(decompress(b'\x04\0\0\0\xe9\x76\xfb\xdd\x9c'), b'FORM')

    def test_lzhuf_rejects_truncation_and_size_bomb(self):
        for raw in (b'', b'\xff\xff\xff\xff', b'\x10\0\0\0'):
            with self.assertRaises(ValueError):decompress(raw)

    def test_rle_boundaries(self):
        for raw in (bytes(8000), bytes(range(256))*31+b'abc', b'a'*131, b'ab'*4000):
            packed=pack(raw);actual,at=unpack(packed,len(raw))
            self.assertEqual(actual,raw);self.assertEqual(at,len(packed))

    def test_rle_rejects_truncation_and_overrun(self):
        for data,size in ((b'\xff\x42',3),(b'\x05ab',6),(b'\x80',3)):
            with self.assertRaises(ValueError):unpack(data,size)

    def test_multifile_d64_roundtrip_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            prg=Path(tmp)/'p';d64=Path(tmp)/'d'
            prg.write_bytes(b'\x01\x08'+b'a'*1000)
            files={f'SCENE{i:02d}':bytes([i])*300 for i in range(20)}
            make_image(prg,d64,files=files)
            self.assertEqual(read_files(d64),{'MEGALOMANIA':prg.read_bytes(),**files})
            data=bytearray(d64.read_bytes());data[OFFSET(18,2):OFFSET(18,2)+2]=bytes((18,1));d64.write_bytes(data)
            with self.assertRaises(ValueError):read_files(d64)

    def test_d64_rejects_duplicate_names_and_full_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'p';p.write_bytes(b'\x01\x08x')
            for files in ({'MEGALOMANIA':b'x'},{'BIG':bytes(180000)}):
                with self.assertRaises(ValueError):make_image(p,Path(tmp)/'d',files=files)


class Streaming(GameCase):
    def open(self,name='TEST',data=b''):
        self.cpu.drive_files[name]=data
        addr=0x200;self.cpu.m[addr:addr+len(name)]=name.encode()
        self.cpu.a=len(name);self.cpu.x=addr&255;self.cpu.y=addr>>8
        self.call('ld_open')

    def test_last_byte_is_valid_and_next_read_fails(self):
        self.open(data=b'AB');self.cpu.x=17;self.cpu.y=33
        self.call('ld_read');self.assertEqual((self.cpu.a,self.cpu.x,self.cpu.y),(65,17,33))
        self.call('ld_read');self.assertEqual(self.cpu.a,66);self.assertFalse(self.cpu.flag(1))
        self.call('ld_read');self.assertTrue(self.cpu.flag(1))

    def test_keyboard_poll_does_not_consume_the_disk_channel(self):
        self.open(data=b'AB')
        self.put('ic_active',1);self.put('vblank',1)
        self.call('intro_poll');self.assertFalse(self.cpu.flag(1))
        self.assertEqual(self.cpu.channels[2][1],0)
        self.assertEqual(self.cpu.input_channel,2)
        self.call('ld_read');self.assertEqual(self.cpu.a,65)
        self.cpu.key=32;self.put('vblank',2)
        self.call('intro_poll');self.assertTrue(self.cpu.flag(1))
        self.assertEqual(self.cpu.channels[2][1],1)

    def test_loader_stops_nmi_and_rejects_missing_drive(self):
        self.cpu.a=0;self.call('sample_play')
        self.open(data=b'AB');self.assertEqual(self.state('smp_left'),0)
        self.cpu.drive_device=9;self.open();self.assertTrue(self.cpu.flag(1))

    def unpack(self,raw,size):
        self.open(data=raw);self.cpu.m[0xfb:0xfd]=b'\x00\xe0'
        self.put('ld_left',size&255);self.put('ld_left',size>>8,1)
        self.call('ld_unpack')

    def test_6502_packet_decoder_matches_python(self):
        raw=bytes(range(128))+b'A'*130+b'B'*3+b'xy'*64
        self.unpack(pack(raw),len(raw))
        self.assertFalse(self.cpu.flag(1));self.assertEqual(bytes(self.cpu.m[0xe000:0xe000+len(raw)]),raw)

    def test_6502_rejects_truncated_packets_and_output_overflow(self):
        self.cpu.m[0xe003]=0x77
        self.unpack(b'\xffA',3);self.assertTrue(self.cpu.flag(1));self.assertEqual(self.cpu.m[0xe003],0x77)
        self.unpack(b'\x05ab',6);self.assertTrue(self.cpu.flag(1))

    def test_intro_scene_validation_and_bank_selection(self):
        raw=encode(bytes([0x55])*8000,bytes([0x12])*1000,bytes([3])*1000,frames=4)
        self.cpu.drive_files['TEST']=raw
        self.cpu.m[0x200:0x204]=b'TEST';self.cpu.a=4;self.cpu.x=0;self.cpu.y=2
        self.put('ic_bank',1);self.call('ic_load')
        self.assertFalse(self.cpu.flag(1))
        self.assertEqual(bytes(self.cpu.m[0xe000:0xe000+8000]),bytes([0x55])*8000)
        self.assertEqual(self.cpu.m[0xcfe8],0) # screen stops before sprite pointer area
        self.call('ic_flip');self.assertEqual(self.cpu.m[0xdd00]&3,0)
        self.assertEqual(self.cpu.m[0xd018],0x38);self.assertEqual(self.cpu.m[0xd016],8)
        self.assertEqual(bytes(self.cpu.m[0xd800:0xdbe8]),bytes([3])*1000)

    def test_no_content_falls_back_to_embedded_title(self):
        boot(self.cpu,self.sym)
        self.assertFalse(self.state('ic_dirty'));self.assertEqual(self.cpu.m[0xd018],0x1e)

    def test_intro_streams_twenty_nine_stages_restores_title(self):
        files={f'SCENE{i:02d}':encode(bytes([i])*8000,bytes([i])*1000,bytes(1000),frames=2) for i in range(1,30)}
        files['TITLE']=encode((ROOT/'assets/intro_bitmap.bin').read_bytes(),(ROOT/'assets/intro_screen.bin').read_bytes(),(ROOT/'assets/intro_color.bin').read_bytes(),multicolor=True,frames=1)
        self.cpu.drive_files=files
        flips=[];self.cpu.m[0x02a6]=1;self.call('irq_install')
        def record(c):
            if c.pc==self.sym['ic_flip']:flips.append(self.state('ic_bank'))
        self.cpu.pc=self.sym['intro_sequence'];self.cpu.push(0xff);self.cpu.push(0xef)
        self.cpu.run_until(0xfff0,max_steps=10000000,on_pc=record)
        self.assertEqual(flips,([1,0]*15)[:29])
        self.assertEqual(bytes(self.cpu.m[0x6000:0x7f40]),(ROOT/'assets/intro_bitmap.bin').read_bytes())
        self.assertEqual(self.cpu.m[0xd018],0x1e)
        self.assertFalse(self.cpu.flag(1));self.assertEqual(self.cpu.channels,{})


class SpeechAndCards(GameCase):
    def bank(self,lengths=None):
        lengths=lengths or [2]*8
        index,offset=bytearray(),0
        for count in lengths:
            address=0x4c80+offset if offset<0x3380 else 0xe000+offset-0x3380
            index+=struct.pack('<HH',address,count*2);offset+=count
        raw=bytearray((i*17+3)&255 for i in range(0x537a))
        return b'MLV1'+index+pack(raw[:0x3380])+pack(raw[0x3380:]),raw

    def load(self,data):
        self.cpu.drive_files['SPEECH']=data;self.cpu.call(self.sym['speech_load'],max_ops=2000000)

    def test_voice_bank_loads_both_regions_without_touching_code_or_vectors(self):
        data,raw=self.bank();self.cpu.m[0xfffa:]=b'VECTOR'
        self.load(data)
        self.assertEqual(self.state('sp_ready'),1)
        self.assertEqual(bytes(self.cpu.m[0x4c80:0x8000]),raw[:0x3380])
        self.assertEqual(bytes(self.cpu.m[0xe000:0xfffa]),raw[0x3380:])
        self.assertEqual(bytes(self.cpu.m[0xfffa:]),b'VECTOR')
        # Loading speech must preserve the original effect sample bank.
        self.assertEqual(bytes(self.cpu.m[self.sym['smp_data']:self.sym['smp_payload_end']]),BLOB_LOCAL())
        self.assertEqual(self.cpu.channels,{})

    def test_invalid_voice_index_is_rejected_before_sample_writes(self):
        data,_=self.bank();data=bytearray(data);data[4:6]=b'\x00\xd0'
        self.cpu.m[0x4c80]=0x77;self.load(data)
        self.assertEqual(self.state('sp_ready'),0);self.assertEqual(self.cpu.m[0x4c80],0x77)

    def test_voice_truncation_leaves_bank_disabled(self):
        data,_=self.bank();self.load(data[:-1]);self.assertEqual(self.state('sp_ready'),0)

    def test_voice_wraps_from_7fff_to_e000_and_restores_cpu_port(self):
        data,_=self.bank([8191,4992,2,2,2,2,2,2]);self.load(data)
        self.assertEqual(self.state('sp_ready'),1)
        self.cpu.m[1]=0x36;self.cpu.m[0x02a6]=1
        self.cpu.a=2;self.call('speech_play')
        self.assertEqual(self.cpu.m[0xdd04],245)
        self.assertEqual(self.cpu.m[self.sym['smp_rd']+1]|self.cpu.m[self.sym['smp_rd']+2]<<8,0x7fff)
        ports=[];step=self.cpu.step
        def observe():
            if self.cpu.pc==self.sym['smp_rd']:ports.append(self.cpu.m[1])
            return step()
        self.cpu.step=observe
        self.call('sample_step');self.call('sample_step')
        self.assertEqual(ports,[0x34,0x34])
        self.assertEqual(self.cpu.m[self.sym['smp_rd']+1]|self.cpu.m[self.sym['smp_rd']+2]<<8,0xe000)
        self.assertEqual(self.cpu.m[1],0x36)

    def test_question_queues_its_reply_and_disk_stop_cancels_it(self):
        data,_=self.bank();self.load(data)
        self.call('speech_question');self.cpu.a=4;self.call('speech_answer')
        self.assertEqual(self.state('sp_queue'),4)
        for _ in range(4):self.call('sample_step')
        self.assertEqual(self.state('sp_id'),4);self.assertEqual(self.state('smp_speech'),1)
        self.assertEqual(self.state('sp_queue'),255)
        self.cpu.a=5;self.call('speech_answer');self.call('disk_begin')
        self.assertEqual(self.state('sp_queue'),255);self.assertEqual(self.state('smp_speech'),0)

    def test_island_card_restores_vic_registers_and_preserves_speech(self):
        self.call('irq_install');self.put('cards_on',1)
        self.cpu.drive_files['ISL01']=b'MLC1'+bytes((0,5,15))+bytes([0x55])*128
        regs=[0x10,0x15,0x17,0x1c,0x1d,0x25,0x26,0x2b,0x2c]+list(range(8,12))
        old=[self.cpu.m[0xd000+i] for i in regs]
        speech=bytes(self.cpu.m[0x4c80:0x8000])+bytes(self.cpu.m[0xe000:0xfffa])
        self.cpu.pc=self.sym['level_card'];self.cpu.push(0xff);self.cpu.push(0xef)
        enabled=[]
        def observe_card(cpu):
            if cpu.pc==self.sym['lc_wait']:enabled.append(cpu.m[0xd015]&0x30)
        self.cpu.run_until(0xfff0,max_steps=1000000,on_pc=observe_card)
        self.assertTrue(enabled);self.assertEqual(set(enabled),{0x30})
        self.assertEqual([self.cpu.m[0xd000+i] for i in regs],old)
        self.assertEqual(bytes(self.cpu.m[0x3400:0x3480]),bytes([0x55])*128)
        self.assertEqual(bytes(self.cpu.m[0x4c80:0x8000])+bytes(self.cpu.m[0xe000:0xfffa]),speech)
        self.assertEqual(self.cpu.channels,{})


def BLOB_LOCAL():
    return (ROOT/'assets/orig/samples.bin').read_bytes()


class ScrollingCredits(GameCase):
    def load_credit(self, steps=390):
        chars=bytes(range(256))*8
        cells=bytes((i//40+i%40)%256 for i in range(3000))
        colors=bytes((i//40)%16 for i in range(3000))
        logo=bytes([0x55])*1600;screen=bytes([0x10])*200
        data=encode_credit(chars,cells,colors,logo,screen,steps)
        self.assertEqual(decode(data)[3],[chars,cells,colors,logo,screen])
        self.cpu.drive_files['TEST']=data
        self.cpu.m[0x200:0x204]=b'TEST';self.cpu.a=4;self.cpu.x=0;self.cpu.y=2
        self.cpu.call(self.sym['ic_load'],max_ops=2000000);self.assertFalse(self.cpu.flag(1))
        self.call('ic_flip')
        return cells,colors,logo,screen

    def test_complete_card_scrolls_without_cropping_or_touching_logo(self):
        cells,colors,logo,screen=self.load_credit()
        self.put('ic_hold',255);self.put('ic_hold',1,1)
        for pixel in range(391):
            row=pixel//8;offset=row*40
            self.assertEqual(bytes(self.cpu.m[0xcc00:0xcf20]),cells[offset:offset+800],pixel)
            self.assertEqual(bytes(self.cpu.m[0xd800:0xdb20]),colors[offset:offset+800],pixel)
            self.assertEqual(self.state('cr_y'),(3-pixel)%8)
            self.assertEqual(bytes(self.cpu.m[0xf900:0xff40]),logo)
            self.assertEqual(bytes(self.cpu.m[0xcb20:0xcbe8]),screen)
            self.assertEqual(bytes(self.cpu.m[0xcf20:0xcfe8]),bytes(200))
            self.assertEqual(bytes(self.cpu.m[0x77c0:0x7e00]),logo)
            if pixel<390:self.call('credit_tick')
        self.assertEqual(self.state('cr_row'),48)

    def test_credit_raster_switch_keeps_logo_fixed(self):
        self.load_credit();self.call('irq_install')
        self.put('ic_active',1);self.put('ic_visible_mode',3);self.put('cr_y',6)
        self.cpu.m[0xd019]=1;self.cpu.run_irq()
        self.assertEqual(self.cpu.m[0xd011],0x1e)
        self.assertEqual(self.cpu.m[0xd012],208)
        self.cpu.m[0xd019]=1;self.cpu.m[0xd012]=210;self.cpu.run_irq()
        self.assertEqual(self.cpu.m[0xd011],0x3b)
        self.assertEqual(self.cpu.m[0xd012],250)
        self.assertEqual(self.state('irq_stage'),0)

    def test_oversized_scroll_is_rejected_before_writing_glyphs(self):
        data=bytearray(encode_credit(bytes(2048),bytes(3000),bytes(3000),bytes(1600),bytes(200),1))
        data[6:8]=struct.pack('<H',401)
        self.cpu.drive_files['TEST']=data
        self.cpu.m[0xe000]=0xa5
        self.cpu.m[0x200:0x204]=b'TEST';self.cpu.a=4;self.cpu.x=0;self.cpu.y=2
        self.call('ic_load');self.assertTrue(self.cpu.flag(1))
        self.assertEqual(self.cpu.m[0xe000],0xa5)
        with self.assertRaises(ValueError):decode(data)


class IntroTimeline(GameCase):
    def test_nominal_vga_clock_advances_seventy_ticks_per_second(self):
        for frames in (50,60):
            self.put('ic_active',1);self.put('ic_skip',0);self.put('ic_visible_mode',0)
            self.put('ic_clock',0);self.put('ic_rate',frames);self.put('ic_vb',0)
            self.put('ic_hold',200);self.put('ic_hold',0,1);self.put('joy_raw',31)
            for i in range(1,frames+1):
                self.put('vblank',i);self.call('intro_poll')
                self.assertFalse(self.cpu.flag(1))
            self.assertEqual(self.state('ic_hold'),130)
            self.assertEqual(self.state('ic_clock'),0)

    def test_text_strip_patch_keeps_the_story_artwork(self):
        from scene_format import encode_story_patch
        self.cpu.m[0xe000:0xf900]=bytes([0xa5])*6400
        self.cpu.m[0xcc00:0xcf20]=bytes([0x3b])*800
        raw=encode_story_patch(bytes([0x55])*1600,bytes([0x10])*200,bytes([7])*200)
        self.cpu.drive_files['TEST']=raw
        self.cpu.m[0x200:0x204]=b'TEST';self.cpu.a=4;self.cpu.x=0;self.cpu.y=2
        self.put('ic_bank',1);self.cpu.call(self.sym['ic_load'],max_ops=2000000)
        self.assertFalse(self.cpu.flag(1))
        self.assertEqual(bytes(self.cpu.m[0xe000:0xf900]),bytes([0xa5])*6400)
        self.assertEqual(bytes(self.cpu.m[0xf900:0xff40]),bytes([0x55])*1600)
        self.assertEqual(bytes(self.cpu.m[0xcc00:0xcf20]),bytes([0x3b])*800)
        self.call('ic_flip');self.assertEqual(self.state('ic_visible_mode'),2)
