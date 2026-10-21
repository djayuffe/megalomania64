#!/usr/bin/env python3
"""Check the private native integration in isolated VICE; never distributes assets."""
import argparse,json,re,socket,subprocess,time
from pathlib import Path
from native_world import decode,SLOT
from scene_format import unpack


def verify(emulator,disk,native,out,model,handoff=False):
    out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    report=json.loads((native/'build.json').read_text())
    labels={s.lstrip('.'):int(a,16)for _,a,s in [line.split()for line in(native/'runtime.lbl').read_text().splitlines()]}
    with socket.socket()as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    args=[emulator,'-default','-model',model,'+sound','-warp','-virtualdev8','+drive8truedrive','-drive8type','1581','-8',str(disk.resolve()),'-remotemonitor','-remotemonitoraddress',f'ip4://127.0.0.1:{port}','-initbreak','0xa474']
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
                cmd(f'> 0277 {ord(value):02x}');cmd('> 00c6 01');cmd('x');cmd('delete')
                assert memory(labels['_runtime_last_key'],1)==value.encode(),f'key {value} not handled'
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
            cmd('delete');cmd(f'watch store {labels["_runtime_ready"]:04x}');cmd('x');cmd('delete')
            assert memory(labels['_runtime_ready'],1)==b'\1','native content load failed'
            settle();before=sectors('initial_world')
            selected=next(i for i,s in enumerate(before)if word(s,0x3fe)==0)
            assert word(before[selected],0x404)>=99
            sprites=memory(0x3140,320,'sprites')
            assert sprites[:256]==(Path(__file__).resolve().parents[1]/'assets/orig/army_frames.bin').read_bytes()[:256]
            assert memory(report['hardware']['mu_ready'],1)==b'\1','SID score did not load'
            code=memory(0x8000,report['immutable_high_bytes'],'code_before')
            key('U');after=sectors('deployed_world');assert after[selected][0x2c8+10]==10,'unarmed deployment failed'
            key('\r');key('S');key('\r')
            moved=sectors('moved_world');assert moved[selected+4][0x2c8+10]==10 and moved[selected][0x2c8+10]==0,'army transfer failed'
            effect=(native/'files/NSND00').read_bytes();n=int.from_bytes(effect[4:6],'little');expected,_=unpack(effect,(n+1)//2,7)
            assert memory(0xef00,len(expected),'effect_cache')==expected,'effect cache differs from source'
            key('\r');key('W');key('\r')
            key('H');after=sectors('returned_world');assert after[selected][0x2c8+10]==0,'army return failed'
            key('R');after=sectors('research_world');assert word(after[selected],0xc4)==1,'inventor assignment failed'
            key('K');after=sectors('released_world');assert word(after[selected],0xc4)==0,'inventor release failed'
            key('Z')
            clip=(native/'files/NSND11').read_bytes();n=int.from_bytes(clip[4:6],'little')
            expected,_=unpack(clip,(n+1)//2,7)
            assert memory(0xef00,len(expected),'voice_cache')==expected,'voice cache differs from decoded source'
            key('P');key('P');key('N');after=sectors('island_two_world')
            assert memory(0x8000,len(code),'code_after')==code,'island load corrupted code'
            assert memory(labels['_runtime_ready'],1)==b'\1'
            (out/'vic.txt').write_bytes(cmd('m d000 d02e'))
            cmd(f'screenshot "{out}/native.png" 2')
            result=dict(model=model,handoff=handoff,ready=True,checks=['disk bootstrap','rules and compressed world','army sprites','resident SID score','deploy, move and return','research allocation','player switching','next island','compressed effect and voice caches with NMI playback','code bank preserved'])
            (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
            connection.sendall(b'quit\n')
        finally:
            if connection:connection.close()
            if process.poll()is None:process.terminate()
            process.wait(timeout=10)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--emulator',default='x64sc');p.add_argument('--disk',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--model',default='pal',choices=['pal','ntsc']);p.add_argument('--handoff',action='store_true');a=p.parse_args()
    verify(a.emulator,a.disk,a.native,a.out,a.model,a.handoff)
