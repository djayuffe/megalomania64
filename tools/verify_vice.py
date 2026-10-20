#!/usr/bin/env python3
"""Verify the full content disk in VICE using the documented TCP monitor.

Runs an isolated emulator process with true 1541 emulation and virtual-device traps
switched off. Saves screenshots, RAM dumps and a monitor transcript outside dist/.
Requires a graphical session (on Linux run under xvfb-run).
"""
import argparse
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from make_d64 import read_files
from scene_format import unpack

ROOT = Path(__file__).resolve().parents[1]


def verify(emulator, disk, out, model="pal"):
    out = out.resolve(); out.mkdir(parents=True, exist_ok=True)
    syms = {n: int(a, 16) for a, n in (line.split() for line in (ROOT / 'dist/symbols.txt').read_text().splitlines())}
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    args = [emulator, '-default', '-model', model, '+sound', '-warp', '-drive8truedrive', '+virtualdev8',
            '-autostart', str(disk.resolve()), '-remotemonitor', '-remotemonitoraddress', f'ip4://127.0.0.1:{port}',
            '-initbreak', str(syms['ic_displayed']), '-limitcycles', '1500000000']
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
                connection.sendall((command+'\n').encode()); return response(timeout)

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

            response(); cmd('delete'); cmd('resourceset "WarpMode" "1"'); screenshot('01_original_credit.png')
            print('VICE: first original credit displayed', flush=True)
            cmd(f'break {syms["ic_displayed"]:04x}')
            cmd('ignore 1 $0e')
            cmd('x')
            screenshot('02_original_story.png')
            cmd('delete')
            cmd(f'until {syms["title_wait"]:04x}')
            if memory(syms['ic_index'], syms['ic_index']) != b'\x15':
                raise AssertionError('did not complete all twenty original scenes')
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
            if memory(syms['mu_mode'],syms['mu_mode'])!=b'\x01':
                raise AssertionError('title did not select choose3 score')
            print('VICE: original SID score bank loaded; title arrangement running',flush=True)
            print('VICE: all twenty scenes loaded; embedded title restored', flush=True)
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
            if memory(syms['mu_mode'],syms['mu_mode'])!=b'\x00':
                raise AssertionError('game did not select war14 score')
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
            print('VICE: voice bank matches RAM; low-RAM and KERNAL-shadow clips completed', flush=True)
            connection.sendall(b'quit\n')
            process.wait(timeout=20)
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
    a = p.parse_args()
    if not a.emulator: p.error('VICE x64sc is required')
    verify(a.emulator, a.disk, a.out, a.model)
