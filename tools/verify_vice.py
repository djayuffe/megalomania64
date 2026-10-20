#!/usr/bin/env python3
"""Verify the full content disk in VICE using the documented TCP monitor.

Runs an isolated emulator process with true 1541 emulation and virtual-device traps
switched off. Saves screenshots, RAM dumps and a monitor transcript outside dist/.
Requires a graphical session (on Linux run under xvfb-run).
"""
import argparse
import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from make_d64 import read_files
from scene_format import unpack, decode

ROOT = Path(__file__).resolve().parents[1]


def verify(emulator, disk, out, model="pal", audio=False, sid_model="6581"):
    out = out.resolve(); out.mkdir(parents=True, exist_ok=True)
    syms = {n: int(a, 16) for a, n in (line.split() for line in (ROOT / 'dist/symbols.txt').read_text().splitlines())}
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    args = [emulator, '-default', '-model', model, '+sound', '-warp', '-drive8truedrive', '+virtualdev8',
            '-autostart', str(disk.resolve()), '-remotemonitor', '-remotemonitoraddress', f'ip4://127.0.0.1:{port}',
            '-initbreak', str(syms['ic_displayed']), '-limitcycles', '1500000000']
    if audio:
        args[args.index('+sound')] = '-sound'
        args += ['-soundoutput','1','-soundwarpmode','1','-sidmodel',{'6581':'0','8580':'1'}[sid_model]]
    with (out / 'vice.log').open('w') as log, (out / 'monitor.txt').open('wb') as transcript:
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
        connection = None
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    connection = socket.create_connection(('127.0.0.1', port), timeout=1); break
                except OSError:
                    if process.poll() is not None: raise RuntimeError('VICE exited; inspect vice.log')
                    time.sleep(.1)
            if connection is None: raise RuntimeError('VICE monitor did not start')
            connection.settimeout(.5)

            def response(timeout=180):
                result = b''; deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    try:
                        chunk = connection.recv(65536)
                    except socket.timeout:
                        continue
                    if not chunk: raise RuntimeError('VICE monitor disconnected')
                    result += chunk; transcript.write(chunk); transcript.flush()
                    if re.search(rb'\(C:\$[0-9a-fA-F]{4}\)\s*$', result): return result
                raise TimeoutError('VICE checkpoint timed out')

            def cmd(command, timeout=180):
                transcript.write(('\nCOMMAND '+command+'\n').encode()); transcript.flush()
                connection.sendall((command+'\n').encode())
                result=response(timeout)
                if b'ERROR --' in result or b'Unknown resource' in result or b'Unknown command' in result:
                    raise RuntimeError(f'VICE rejected {command}: {result.decode("latin1")}')
                return result

            def screenshot(name):
                cmd('step $4e20')  # allow the VIC to finish at least one frame
                cmd(f'screenshot "{out / name}" 2')
            def memory(start, end):
                reply = cmd(f'm {start:04x} {end:04x}')
                data = bytearray()
                for line in reply.decode('latin1').splitlines():
                    match = re.search(r'>C:[0-9a-fA-F]{4}\s+((?:[0-9a-fA-F]{2}\s+)+)', line)
                    if match: data.extend(bytes.fromhex(match.group(1)))
                if len(data) != end-start+1: raise RuntimeError(f'monitor parse: {reply!r}')
                return bytes(data)

            response(); cmd('delete'); cmd('warp on'); screenshot('01_original_story.png')
            if audio and memory(syms['sid_8580'],syms['sid_8580'])!=bytes([int(sid_model=='8580')]):
                raise AssertionError('SID revision detection selected the wrong digi gain')
            print('VICE: first original story displayed', flush=True)
            cmd(f'break {syms["ic_displayed"]:04x}')
            cmd('ignore 1 $0d')
            cmd('x')
            cmd('delete')
            if memory(syms['ic_index'],syms['ic_index']) != b'\x0f':
                raise AssertionError('credits did not follow fourteen story stages')
            credit=decode(read_files(disk)['SCENE15'])[3]
            cmd('bank ram')
            cmd(f'bsave "{out / "credit_charset.bin"}" 0 e000 e7ff')
            if (out/'credit_charset.bin').read_bytes()!=credit[0]:
                raise AssertionError('credit glyphs differ from disk')
            cmd(f'bsave "{out / "credit_logo.bin"}" 0 f900 ff3f')
            if (out/'credit_logo.bin').read_bytes()!=credit[3]:
                raise AssertionError('fixed logo bitmap differs from disk')
            cmd('bank cpu')
            cmd(f'break {syms["credit_tick"]:04x}');cmd('ignore 1 $63');cmd('x');cmd('delete')
            screenshot('02_scrolling_credit.png')
            cmd('delete')
            # Freeze the main loop and exercise every fine-scroll phase. IRQs
            # still run, so this checks the actual VIC character-row counter.
            saved_regs=cmd('registers').decode('latin1')
            saved_pc=int(re.search(r'\.;([0-9a-fA-F]{4})',saved_regs).group(1),16)
            saved_fine=memory(syms['cr_y'],syms['cr_y'])[0]
            wait=syms['wait_frame']
            # Preserve the complete interrupted CPU context with native 6502
            # pushes/pulls. Restoring PC alone can corrupt an active copy loop.
            cmd(f'> 0240 08 48 8a 48 98 48 a2 03 20 {wait&255:02x} {wait>>8:02x} ca d0 fa 4c 4e 02 68 a8 68 aa 68 28 4c {saved_pc&255:02x} {saved_pc>>8:02x}')
            for phase in range(8):
                cmd(f'> {syms["cr_y"]:04x} {phase:02x}')
                cmd('registers pc='+('0240' if phase==0 else '0246'));cmd('until 024e')
                cmd(f'screenshot "{out / ("credit_phase_"+str(phase)+".png")}" 2')
            cmd(f'> {syms["cr_y"]:04x} {saved_fine:02x}')
            cmd(f'> {syms["ic_vb"]:04x} {memory(syms["vblank"],syms["vblank"])[0]:02x}')
            cmd('registers pc=0251');cmd(f'until {saved_pc:04x}')
            from PIL import Image
            # VICE crops PAL at raster 16 and NTSC at 28; logo is 211..250.
            logo_y=195 if model=="pal" else 183
            logos=[Image.open(out/f'credit_phase_{phase}.png').convert('RGB').crop((32,logo_y,352,logo_y+40)).tobytes() for phase in range(8)]
            if not any(logos[0]):raise AssertionError("fixed logo capture is blank")
            if any(logo != logos[0] for logo in logos[1:]):
                raise AssertionError('fixed logo moved or changed across fine-scroll phases')
            print('VICE: fixed logo pixels match across all eight scroll phases',flush=True)
            cmd(f'until {syms["title_wait"]:04x}')
            if memory(syms['ic_index'], syms['ic_index']) != b'\x1e':
                raise AssertionError('did not complete all twenty-nine original intro stages')
            if memory(syms['ic_skip'], syms['ic_skip']) != b'\x00':
                raise AssertionError('intro aborted')
            if memory(syms['mu_ready'],syms['mu_ready'])!=b'\x01':
                raise AssertionError('original SID score bank did not load')
            cmd('bank ram')
            music=read_files(disk)['MUSIC'][6:]
            cmd(f'bsave "{out / "music_bank.bin"}" 0 c400 {0xc400+len(music)-1:04x}')
            if (out/'music_bank.bin').read_bytes()!=music:
                raise AssertionError('original SID score RAM differs from disk')
            cmd('bank cpu')
            cmd(f'until {syms["original_music_tick"]:04x}')  # wait for the parade/sample hold to end
            screenshot('03_native_title.png')
            if memory(syms['mu_mode'],syms['mu_mode'])!=b'\x00':
                raise AssertionError('title did not select choose3 score')
            def record(name, frames):
                if not audio:return
                cmd('warp off')
                cmd(f'resourceset "SoundRecordDeviceArg" "{out / (name+".wav")}"')
                cmd('resourceset "SoundRecordDeviceName" "wav"')
                # Loop a frame-synchronized stub without involving the game loop.
                registers=cmd('registers').decode('latin1')
                saved=int(re.search(r'\.;([0-9a-fA-F]{4})',registers).group(1),16)
                wait=syms['wait_frame']
                cmd(f'> 0240 a2 {frames:02x} 20 {wait&255:02x} {wait>>8:02x} ca d0 fa 4c 48 02')
                cmd('registers pc=0240');cmd('until 0248')
                cmd(f'resourceset "SoundRecordDeviceArg" "{os.devnull}"')
                cmd('warp on')
                cmd(f'registers pc={saved:04x}')
            cmd(f'until {syms["title_wait"]:04x}')
            record('title_music',250)
            print('VICE: original SID score bank loaded; title arrangement running',flush=True)
            print('VICE: all twenty-nine intro stages loaded; embedded title restored', flush=True)
            cmd('> 0277 20'); cmd('> 00c6 01')
            cmd(f'until {syms["lc_wait"]:04x}')
            card_regs=memory(0xd000,0xd02e)
            card_ptrs=memory(0x07fc,0x07fd)
            card_bank=memory(0xdd00,0xdd00)[0]&3
            card_data=memory(0x3400,0x347f)
            (out/'card_registers.txt').write_text(f'bank={card_bank} pointers={card_ptrs.hex()} registers={card_regs.hex()}\n')
            print(f'VICE card: bank {card_bank}, enable {card_regs[0x15]:02x}, priority {card_regs[0x1b]:02x}, pointers {card_ptrs.hex()}',flush=True)
            if card_bank!=3 or card_ptrs!=b'\xd0\xd1' or card_regs[0x15]&0x30!=0x30:
                raise AssertionError('island sprite setup')
            if card_data != read_files(disk)['ISL01'][7:]:
                raise AssertionError('island sprite payload differs from disk')
            screenshot('04_island_card.png')
            cmd(f'until {syms["main_loop"]:04x}')
            if memory(syms['sp_ready'], syms['sp_ready']) != b'\x01':
                raise AssertionError('resident speech bank did not load')
            screenshot('05_game.png')
            if memory(syms['mu_mode'],syms['mu_mode'])!=b'\x01':
                raise AssertionError('game did not select war14 score')
            game_music=read_files(disk)['MUSICG'][6:]
            cmd('bank ram')
            cmd(f'bsave "{out / "game_music_bank.bin"}" 0 c400 {0xc400+len(game_music)-1:04x}')
            if (out/'game_music_bank.bin').read_bytes()!=game_music:
                raise AssertionError('game score RAM beneath I/O differs from disk')
            effects=read_files(disk)['EFFECTS']
            primary,offset=unpack(effects,9000,4);tail,offset=unpack(effects,3072,offset)
            cmd(f'bsave "{out / "effects_primary.bin"}" 0 {syms["smp_data"]:04x} {syms["smp_end"]-1:04x}')
            cmd(f'bsave "{out / "effects_tail.bin"}" 0 d400 dfff')
            if (out/'effects_primary.bin').read_bytes()!=primary or (out/'effects_tail.bin').read_bytes()!=tail:
                raise AssertionError('full effect RAM differs from disk')
            cmd('bank cpu')
            cmd(f'until {syms["main_loop"]:04x}')
            record('game_music',250)
            cmd('bank ram')
            cmd(f'bsave "{out / "speech_low.bin"}" 0 4c80 7fff')
            cmd(f'bsave "{out / "speech_high.bin"}" 0 e000 fff9')
            packed = read_files(disk)['SPEECH']
            low, at = unpack(packed, 0x3380, 36)
            high, at = unpack(packed, 0x1ffa, at)
            if (out/'speech_low.bin').read_bytes() != low or (out/'speech_high.bin').read_bytes() != high:
                raise AssertionError('VICE speech RAM differs from the disk payload')
            cmd('bank cpu')
            # Controlled test stub: first a low-RAM clip, then one crossing into
            # RAM under KERNAL. Resume out of the NMI between these checks.
            entry = syms['speech_play']
            for voice in (0,5):
                cmd(f'> 0200 a9 {voice:02x} 20 {entry & 255:02x} {entry >> 8:02x} 4c 05 02')
                cmd(f'break {syms["sample_finished"]:04x}')
                cmd('g 0200')
                if memory(syms['smp_left'], syms['smp_left']+1) != b'\x00\x00':
                    raise AssertionError('voice did not finish')
                index=packed[4+voice*4:8+voice*4]
                address=int.from_bytes(index[:2],'little')
                end=address+int.from_bytes(index[2:],'little')//2
                if address<0x8000<=end: end+=0x6000
                if memory(syms['smp_rd']+1,syms['smp_rd']+2)!=end.to_bytes(2,'little'):
                    raise AssertionError('voice pointer did not reach its exact end')
                cmd('delete');cmd('until 0205')
            if audio:
                for name,routine,clip in [('effect_orchestra','sample_play',9),('original_speech','speech_play',0)]:
                    entry=syms[routine]
                    cmd(f'> 0250 a9 {clip:02x} 20 {entry&255:02x} {entry>>8:02x} 4c 55 02')
                    cmd('registers pc=0250');cmd('until 0255')
                    record(name,120)
                    if memory(syms['smp_left'],syms['smp_left']+1)!=b'\x00\x00':
                        raise AssertionError(f'{name}: timed playback did not finish')
            print('VICE: voice bank matches RAM; low-RAM and KERNAL-shadow clips completed', flush=True)
            connection.sendall(b'quit\n')
            process.wait(timeout=20)
            if audio:
                import array,json,math,wave
                metrics={}
                for name in ['title_music','game_music','effect_orchestra','original_speech']:
                    with wave.open(str(out/(name+'.wav'))) as wav:
                        if wav.getsampwidth()!=2 or wav.getnchannels()!=1:
                            raise AssertionError('expected mono 16-bit PCM audio')
                        rate=wav.getframerate();samples=array.array('h',wav.readframes(wav.getnframes()))
                    if len(samples)<rate:raise AssertionError('audio recorder produced fewer than one second of PCM')
                    rms=math.sqrt(sum(v*v for v in samples)/len(samples))
                    if rms<10:raise AssertionError(f'{name}: silent audio capture')
                    metrics[name]=dict(seconds=len(samples)/rate,rms=rms,peak=max(map(abs,samples)),
                        clipped_fraction=sum(abs(v)>=32767 for v in samples)/len(samples))
                (out/'audio_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
                print(f'VICE: non-silent PCM verified on {sid_model}: '+str(metrics),flush=True)
        finally:
            if connection: connection.close()
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill(); process.wait()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--emulator', default=shutil.which('x64sc'))
    p.add_argument('--disk', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--model',choices=['pal','ntsc'],default='pal')
    p.add_argument('--audio',action='store_true',help='capture title/game music, a full effect and speech as WAV')
    p.add_argument('--sid-model',choices=['6581','8580'],default='6581')
    a = p.parse_args()
    if not a.emulator: p.error('VICE x64sc is required')
    verify(a.emulator, a.disk, a.out, a.model, a.audio, a.sid_model)
