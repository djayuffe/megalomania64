#!/usr/bin/env python3
"""Check the private native integration in isolated VICE; never distributes assets."""
import argparse,json,re,shutil,socket,subprocess,time
from pathlib import Path
from native_world import decode,encode,SLOT
from scene_format import unpack


def verify(emulator,disk,native,out,model,handoff=False,expect_load=None,expect_reject=False):
    out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    report=json.loads((native/'build.json').read_text())
    work_disk=out/'test.d81';shutil.copyfile(disk,work_disk)
    labels={s.lstrip('.'):int(a,16)for _,a,s in [line.split()for line in(native/'runtime.lbl').read_text().splitlines()]}
    with socket.socket()as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    args=[emulator,'-default','-model',model,'+sound','-warp','-virtualdev8','+drive8truedrive','-drive8type','1581','-8',str(work_disk),'-remotemonitor','-remotemonitoraddress',f'ip4://127.0.0.1:{port}','-initbreak','0xa474']
    with(out/'vice.log').open('w')as log,(out/'monitor.txt').open('wb')as transcript:
        process=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT);connection=None
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:connection=socket.create_connection(('127.0.0.1',port),timeout=.5);break
                except OSError:
                    if process.poll()is not None:raise RuntimeError('VICE exited')
                    time.sleep(.1)
            if connection is None:raise RuntimeError('monitor unavailable')
            connection.settimeout(.5)
            def response():
                data=b'';deadline=time.monotonic()+45
                while time.monotonic()<deadline:
                    try:chunk=connection.recv(65536)
                    except socket.timeout:continue
                    if not chunk:raise RuntimeError('monitor disconnected')
                    data+=chunk
                    if re.search(rb'\(C:\$[0-9a-fA-F]{4}\)\s*$',data):
                        transcript.write(data);transcript.flush();return data
                raise TimeoutError(data[-1000:])
            def cmd(command):
                transcript.write(command.encode()+b'\n');connection.sendall((command+'\n').encode());result=response()
                if b'ERROR --'in result:raise RuntimeError(result)
                return result
            def memory(first,size,name='memory'):
                path=out/(name+'.bin');cmd('bank ram');cmd(f'bsave "{path}" 0 {first:04x} {first+size-1:04x}');cmd('bank cpu')
                data=path.read_bytes()
                if len(data)!=size:raise AssertionError(f'invalid memory dump: {len(data)} != {size}')
                return data
            def settle():
                cmd('delete');cmd(f'watch store {labels["_runtime_drawn"]:04x}');cmd('x');cmd('delete')
                cmd(f'watch store {report["hardware"]["native_frames"]:04x}');cmd('x');cmd('x');cmd('delete')
            def key(value):
                cmd('delete');cmd(f'watch store {labels["_runtime_last_key"]:04x}')
                cmd(f'> 0277 {ord(value):02x}');cmd('> 00c6 01');cmd('step $2000000');cmd('delete')
                if memory(labels['_runtime_last_key'],1)!=value.encode('latin1'):
                    print(cmd('r').decode('latin1'));print(cmd('m 0000 001b').decode('latin1'))
                    memory(0xd400,(native/'runtime.bin.bank').stat().st_size,'failed_code_bank')
                    raise AssertionError(f'key {ord(value)} not handled')
                settle()
            def sectors(name):
                raw=memory(0x4000,SLOT*16,name)
                first,last=memory(labels['_world_first'],2)
                return [decode(raw[i*SLOT:(i+1)*SLOT],first,last)for i in range(16)]
            def word(raw,at):return int.from_bytes(raw[at:at+2],'little')
            response();cmd('delete')
            if handoff:
                root=Path(__file__).resolve().parents[1]
                main_symbols={name:int(at,16)for at,name in [line.split()for line in(root/'dist/symbols.txt').read_text().splitlines()]}
                cmd(f'load "{root}/dist/MegaLoMania64.prg" 0');entry=main_symbols['native_start']
            else:
                cmd(f'load "{native.resolve()}/files/NGSTART" 0');entry=0x080d
            cmd(f'break {report["runtime_main"]:04x}');cmd(f'break {report["boot_error"]:04x}')
            result=cmd(f'g {entry:04x}');assert f'(C:${report["runtime_main"]:04x})'.encode()in result,'boot did not enter runtime'
            cmd('> c200 '+'a5 '*32)
            cmd('delete');cmd(f'watch store {labels["_runtime_ready"]:04x}');cmd('x');cmd('delete')
            assert memory(labels['_runtime_ready'],1)==b'\1','native content load failed'
            state=labels['_ng_state'];cmd(f'> {state+23:04x} 01')
            settle()
            if memory(state+126,1)==b'\1':
                key('+');assert memory(state+118,2)==bytes([30,0])
                key('-');assert memory(state+118,2)==bytes([20,0])
                for expected_island in [1,2,0]:
                    key('N');assert memory(state+12,1)==bytes([expected_island])
                key('\r');assert memory(state+116,2)==bytes([80,0])
            before=sectors('initial_world')
            selected=next(i for i,s in enumerate(before)if word(s,0x3fe)==0)
            assert word(before[selected],0x404)==19
            art=(native/'files/NART01').read_bytes();font,_=unpack(art,2048,4)
            assert memory(0x3800,2048,'terrain_font')==font,'original terrain font differs from disk'
            aux=(native/'runtime.bin.aux').read_bytes()
            assert memory(0x0800,len(aux),'reclaimed_bootstrap')==aux,'bootstrap RAM was not reclaimed for game code'
            sprites=memory(0x3140,320,'sprites')
            assert sprites[:256]==(Path(__file__).resolve().parents[1]/'assets/orig/army_frames.bin').read_bytes()[:256]
            assert memory(report['hardware']['mu_ready'],1)==b'\1','SID score did not load'
            code=memory(0x8000,report['immutable_high_bytes'],'code_before')
            code_bank=memory(0xd400,(native/'runtime.bin.bank').stat().st_size,'bank_before')
            if expect_load or expect_reject:
                key(' ');unchanged=memory(0x4000,SLOT*16,'before_load')
                key(chr(136));restored=memory(0x4000,SLOT*16,'after_load')
                if expect_load:assert restored==expect_load.read_bytes(),'previous valid save was not restored'
                else:assert restored==unchanged,'invalid save modified the current world'
                assert memory(0xd400,len(code_bank),'bank_after')==code_bank,'load recovery corrupted banked code'
                assert memory(0xc200,32,'stack_guard')==bytes([0xa5])*32,'software stack overflow'
                result=dict(model=model,ready=True,recovery='fallback to previous valid save'if expect_load else'invalid saves rejected without state loss')
                (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));connection.sendall(b'quit\n');return
            key('U');after=sectors('deployed_world');assert after[selected][0x2c8+10]==10,'unarmed deployment failed'
            key('\r');key('S');key('\r')
            moved=sectors('moved_world');assert moved[selected+4][0x2c8+10]==10 and moved[selected][0x2c8+10]==0,'army transfer failed'
            effect=(native/'files/NSND00').read_bytes();n=int.from_bytes(effect[4:6],'little');expected,_=unpack(effect,(n+1)//2,7)
            assert memory(0xef00,len(expected),'effect_cache')==expected,'effect cache differs from source'
            key('\r');key('W');key('\r')
            key('H');after=sectors('returned_world');assert after[selected][0x2c8+10]==0,'army return failed'
            damaged=sectors('before_repair');record=damaged[selected]
            record[0x122]|=1;record[0x19c:0x1a6]=bytes([0,1]+[255,0]*4)
            record[0x174:0x176]=(500).to_bytes(2,'little');record[0x3d6:0x3d8]=(50).to_bytes(2,'little')
            fixture=out/'repair-sector.prg';fixture.write_bytes((0x4000+selected*SLOT).to_bytes(2,'little')+encode(record,0,3))
            cmd(f'load "{fixture}" 0');key('C');key('8')
            repaired=sectors('repaired_world')[selected]
            assert word(repaired,0x3d6)==100 and word(repaired,0x174)==499,'shield repair/payment failed'
            key('C');key('C')
            key('R');after=sectors('research_world');assert word(after[selected],0xc4)==1,'inventor assignment failed'
            key('K');after=sectors('released_world');assert word(after[selected],0xc4)==0,'inventor release failed'
            cmd(f'> {labels["_ng_event"]:04x} 01');key('Z')
            clip=(native/'files/NSND11').read_bytes();n=int.from_bytes(clip[4:6],'little')
            expected,_=unpack(clip,(n+1)//2,7)
            assert memory(0xef00,len(expected),'voice_cache')==expected,'voice cache differs from decoded source'
            key('P');key('P');key(' ')
            snapshot=memory(0x4000,SLOT*16,'saved_world')
            key(chr(135));assert memory(state+8,2)==b'\1\0','disk save failed';key('U');assert memory(0x4000,SLOT*16,'changed_world')!=snapshot
            key(chr(136));assert memory(0x4000,SLOT*16,'restored_world')==snapshot,'save/load round trip changed the world'
            key('U');second=memory(0x4000,SLOT*16,'second_saved_world');key(chr(135))
            assert memory(state+8,2)==b'\2\0','second save did not rotate slots'
            key('H');key(chr(136));assert memory(0x4000,SLOT*16,'newest_world')==second,'newest valid save was not selected'
            key('H')
            # Exercise a real AI turn and its disk overlay. Stop after the
            # economy calls return, before its tactical move is chosen.
            cmd(f'> {state+23:04x} 00');cmd(f'> {state+17:04x} 00')
            cmd(f'break {labels["_ng_route_mask"]:04x}');cmd('x');cmd('delete')
            persona=memory(labels['_gp_personality'],56,'ai_personality')
            plan=memory(labels['_gp_plan'],28,'ai_worker_plan')
            assert any(persona) and any(plan),'AI overlay did not plan a turn'
            assert memory(0xc200,32,'ai_stack_guard')==bytes([0xa5])*32,'AI overflowed software stack'
            cmd(f'> {state+17:04x} 01');cmd(f'> {state+23:04x} 01');settle()
            key('N');assert memory(state+12,1)==b'\0','campaign advanced before victory'
            key(' ')
            # Destroyed-enemy fixture exercises cache refresh, outcome detection
            # and the next-island UI; detailed combat is checked separately.
            current=sectors('before_victory');enemy=next(i for i,s in enumerate(current)if word(s,0x3fe)in (1,2,3))
            current[enemy][0x448]=(current[enemy][0x448]&127)|64
            fixture=out/'defeated-sector.prg';fixture.write_bytes((0x4000+enemy*SLOT).to_bytes(2,'little')+encode(current[enemy],0,3))
            cmd(f'load "{fixture}" 0');cmd(f'watch store {state+15:04x}');cmd('x');cmd('delete')
            assert memory(state+15,1)==b'\1','victory was not detected'
            key('N');key('\r');after=sectors('island_two_world');assert memory(state+12,1)==b'\1'
            assert memory(0x8000,len(code),'code_after')==code,'island load corrupted code'
            assert memory(0xd400,len(code_bank),'bank_after')==code_bank,'banked code was not preserved'
            assert memory(0xc200,32,'stack_guard')==bytes([0xa5])*32,'software stack overflow'
            assert memory(labels['_runtime_ready'],1)==b'\1'
            # An exhausted deployment pool creates a legitimate zero-faction
            # defeat screen. It must remain saveable and restartable.
            cmd(f'> {state+116:04x} 00 00');cmd(f'> {state+15:04x} 01')
            key('N');assert memory(state+15,1)==b'\2' and memory(state+14,1)==b'\0'
            key(chr(135));key(chr(136));assert memory(state+15,1)==b'\2','defeat save failed to load'
            key('P');key('N');assert memory(state+126,1)==b'\1' and memory(state+116,2)==bytes([100,0])
            assert memory(0xc200,32,'final_stack_guard')==bytes([0xa5])*32,'restart overflowed software stack'
            (out/'vic.txt').write_bytes(cmd('m d000 d02e'))
            cmd(f'screenshot "{out}/native.png" 2')
            result=dict(model=model,handoff=handoff,ready=True,checks=['clean RAM bootstrap and frozen intro handoff','reclaimed bootstrap graphics loader','original terrain glyphs','original deployment population, randomized faction order, campaign pool and island selection','rules and compressed world','army sprites','resident SID score','deploy, move and return','research allocation','live personality-based AI economy overlay','shield repair and payment','player switching','CRC save/load round trip','victory and next island','pool exhaustion, defeat save and restart','compressed effect and voice caches with NMI playback','code bank preserved'])
            (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
            connection.sendall(b'quit\n')
        finally:
            if connection:connection.close()
            if process.poll()is None:process.terminate()
            process.wait(timeout=10)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--emulator',default='x64sc');p.add_argument('--disk',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--model',default='pal',choices=['pal','ntsc']);p.add_argument('--handoff',action='store_true');p.add_argument('--expect-load',type=Path);p.add_argument('--expect-reject',action='store_true');a=p.parse_args()
    verify(a.emulator,a.disk,a.native,a.out,a.model,a.handoff,a.expect_load,a.expect_reject)
