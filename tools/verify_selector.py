#!/usr/bin/env python3
"""Exercise the independent selector, streamed previews and game handoff in VICE."""
import argparse,json,re,shutil,socket,subprocess,time
from pathlib import Path

def verify(emulator,disk,native,out,model,all_scenes=False):
    out=out.resolve();out.mkdir(parents=True,exist_ok=True);native=native.resolve()
    (out/'verification.json').unlink(missing_ok=True)
    shutil.copyfile(disk,out/'test.d81');catalog=json.loads((native/'files/NGSELECT.json').read_text());s=catalog['symbols']
    build=json.loads((native/'build.json').read_text());labels={n.lstrip('.'):int(a,16)for _,a,n in [x.split()for x in(native/'runtime.lbl').read_text().splitlines()]}
    frozen={n:int(a,16)for a,n in [x.split()for x in(Path(__file__).resolve().parents[1]/'dist/symbols.txt').read_text().splitlines()]}
    with socket.socket()as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    with(out/'vice.log').open('w')as log,(out/'monitor.txt').open('wb')as transcript:
        process=subprocess.Popen([emulator,'-default','-model',model,'+sound','-warp','-virtualdev8','+drive8truedrive','-drive8type','1581','-8',str(out/'test.d81'),'-remotemonitor','-remotemonitoraddress',f'ip4://127.0.0.1:{port}','-initbreak','0xa474'],stdout=log,stderr=subprocess.STDOUT);connection=None
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:connection=socket.create_connection(('127.0.0.1',port),timeout=.5);break
                except OSError:time.sleep(.1)
            if connection is None:raise RuntimeError('monitor unavailable')
            connection.settimeout(.5)
            def response():
                data=b'';deadline=time.monotonic()+45
                while time.monotonic()<deadline:
                    try:data+=connection.recv(65536)
                    except socket.timeout:continue
                    if re.search(rb'\(C:\$[0-9a-fA-F]{4}\)\s*$',data):transcript.write(data);transcript.flush();return data
                raise TimeoutError(data[-1000:])
            def cmd(command):
                transcript.write(command.encode()+b'\n');connection.sendall((command+'\n').encode());result=response()
                if b'ERROR --'in result:raise RuntimeError(result)
                return result
            def mem(at,size):
                path=out/'memory.bin';cmd('bank ram');cmd(f'bsave "{path}" 0 {at:04x} {at+size-1:04x}');cmd('bank cpu');return path.read_bytes()
            def run(at,entry=None):
                cmd('delete');cmd(f'break {at:04x}');stopped=cmd('x'if entry is None else f'g {entry:04x}');cmd('delete')
                assert re.search(rb'Stop on\s+exec',stopped) and f'(C:${at:04x})'.encode()in stopped,stopped
            def key(value,at):
                cmd(f'> 0277 {ord(value):02x}');cmd('> 00c6 01');run(at)
            def frames(n=2):
                cmd(f'watch store {frozen["vblank"]:04x}')
                for _ in range(n):cmd('x')
                cmd('delete')
            response();cmd('delete');cmd(f'load "{native}/files/NGSELECT" 0');run(s['sel_wait'],0x1000)
            key('A',s['sel_wait']);assert mem(s['sel_index'],1)==bytes([28])
            key('D',s['sel_wait']);assert mem(s['sel_index'],1)==b'\0'
            key('2',s['sel_wait']);key('9',s['sel_wait']);assert mem(s['sel_index'],1)==bytes([28])
            frames();run(s['sel_wait']);cmd(f'screenshot "{out}/selector.png" 2')
            scenes=list(range(29))if all_scenes else [0,2,6,13,14,28]
            for i in scenes:
                cmd(f'> {s["sel_index"]:04x} {i:02x}');key('\r',s['sel_preview_wait'])
                mode=mem(frozen['ic_mode'],1)[0];visible=mem(frozen['ic_visible_mode'],1)[0]
                assert visible==(2 if mode==4 else mode),(i,mode,visible)
                assert mem(frozen['ic_skip'],1)==b'\0',(i,'preview load failed')
                if mode==3:
                    cmd(f'watch store {frozen["cr_phase"]:04x}');cmd('x');cmd('delete')
                    assert mem(frozen['cr_phase'],1)!=b'\0','credit scroll did not advance'
                if i in [0,2,14,28]:
                    if mode==3:
                        cmd(f'watch store {frozen["cr_row"]:04x}')
                        for _ in range(24 if i==14 else 8):cmd('x')
                        cmd('delete')
                    frames();run(s['sel_preview_wait']);cmd(f'screenshot "{out}/scene-{i+1:02d}.png" 2')
                key(' ',s['sel_wait'])
                assert mem(frozen['ic_active'],1)==b'\0'
            key('G',s['sel_wait']);key('A',s['sel_wait']);assert mem(s['sel_index'],1)==bytes([27])
            key('\r',build['runtime_main']);cmd(f'watch store {labels["_runtime_ready"]:04x}');cmd('x');cmd('delete')
            state=mem(labels['_ng_state'],128)
            assert state[12]==27 and state[126]==1,'selected island did not reach gameplay preparation'
            assert state[42:50]==b'\xe8\x03'*4,'standalone final battle reserves missing'
            assert mem(0x02f0,1)==b'\0','launch request was not consumed'
            expected=(native/'runtime.bin.low').read_bytes();assert mem(0x1000,len(expected))==expected,'selector code retained in game RAM'
            result=dict(model=model,previews=[i+1 for i in scenes],checks=['keyboard navigation and wrap','two-digit selection','story background restoration','credit scrolling','return to independent menu','island 28 fresh checkpoint','one-shot request consumed','selector RAM reclaimed by gameplay'],intro_frozen=True)
            (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));connection.sendall(b'quit\n')
        finally:
            if connection:connection.close()
            if process.poll()is None:process.terminate()
            process.wait(timeout=10)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--emulator',default='x64sc');p.add_argument('--disk',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--model',choices=['pal','ntsc'],default='pal');p.add_argument('--all-scenes',action='store_true');a=p.parse_args();verify(a.emulator,a.disk,a.native,a.out,a.model,a.all_scenes)
