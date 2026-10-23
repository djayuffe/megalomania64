#!/usr/bin/env python3
"""Compare the DOS negotiation state machine with C and banked 6502.

The speech callback is modeled as starting playback (ready=0). Fixtures control
its later completion independently of the decision state machine.
"""
import argparse,ctypes,json,random,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from cpu6502 import CPU
from gameplay_oracle import Oracle

def put(b,at,n):struct.pack_into('<H',b,at,n&65535)
def word(b,at):return struct.unpack_from('<H',b,at)[0]
def verify(dos,native,out,cases=2048):
    out=out.resolve();native=native.resolve()
    if out.is_relative_to(ROOT):raise ValueError('keep original-derived evidence outside checkout')
    out.mkdir(parents=True,exist_ok=True);(out/'verification.json').unlink(missing_ok=True)
    oracle=Oracle(dos,out/'oracle');rng=random.Random(0x2a84)
    subprocess.run(['clang','-O2','-shared','-fPIC','-o',str(out/'diplomacy.dylib'),*[str(ROOT/f'src/gameplay/{n}.c')for n in ['core','ai','tactics','military','diplomacy','strategy','world','game','campaign']]],check=True,capture_output=True)
    lib=ctypes.CDLL(str(out/'diplomacy.dylib'));labels={s.lstrip('.'):int(a,16)for _,a,s in [line.split()for line in(native/'runtime.lbl').read_text().splitlines()]}
    cpu=CPU(native/'files/NGHIGH')
    for name in ['NGLOW','NGEXTRA','NGDRAW','NGTEXT']:
        raw=(native/'files'/name).read_bytes();at=word(raw,0);cpu.m[at:at+len(raw)-2]=raw[2:]
    raw=(native/'runtime.bin.bank').read_bytes();cpu.m[0xd400:0xd400+len(raw)]=raw;cpu.ram_io[:min(4096,len(raw))]=raw[:4096]
    raw=(native/'runtime.bin.diplomacy').read_bytes();cpu.m[0xef00:0xef00+len(raw)]=raw;cpu.m[1]=0x34
    from unicorn import UC_HOOK_CODE
    events=[]
    def speech(u,address,size,data):
        events.append((oracle.word(0x99f0),oracle.word(0x99f4)));oracle.word(0x19ba,0)
        m=oracle.machine;sp=m.r('sp');ip,cs=struct.unpack('<HH',u.mem_read(m.r('ss')*16+sp,4));m.w('sp',sp+4);m.w('cs',cs);m.w('ip',ip)
    at=(oracle.machine.module_seg+0x1a17)*16+0x19c6;oracle.u.hook_add(UC_HOOK_CODE,speech,None,at,at)
    def upload(name,data):
        (ctypes.c_uint8*len(data)).in_dll(lib,name)[:]=data;at=labels['_'+name];cpu.m[at:at+len(data)]=data
    partitions=[bytes([1,2,4,8]),bytes([3,3,4,8]),bytes([5,2,5,8]),bytes([15]*4),bytes([3,3,12,12])]
    counts={'speech':0,'changed_groups':0,'proposals':0,'closed':0,'human_input':0}
    for case in range(cases):
        f=case%4;human=case//4%4;persona=struct.pack('<28H',*oracle.rules['personalities'][case//16%4]);allies=partitions[case//64%len(partitions)]
        d=bytearray(32);d[30]=255;d[31]=255;init=rng.randrange(4);put(d,0,init)
        for at in [4,6,8,10,12,14,16]:put(d,at,rng.randrange(2))
        d[18]=rng.randrange(16);d[19]=allies[(init+1)%4];d[28]=rng.randrange(16);d[29]=rng.randrange(16)
        if case%3==0:put(d,4,0);put(d,16,1)
        if case%7==0:put(d,4,1);put(d,12,0);put(d,16,1);d[18]=1<<f
        clock=rng.randrange(65536)
        for i in range(4):put(d,20+i*2,clock-rng.choice([0,1,999,1000,1500,2000,3000,65535]))
        request=bytearray(32);request[0]=255
        for at,n in [(2,f),(4,case%3==0),(6,case%5==0),(10,rng.randrange(65536)),(14,clock),(16,case//256%3),(18,case//768%2),(26,human),(30,[15,7,5,1][case//128%4])]:put(request,at,n)
        # A live proposal always targets a group with an active member. The
        # DOS acceptance path otherwise rejection-samples an empty mask forever.
        if not(d[19]&request[30]):d[19]=allies[next(i for i in range(4)if request[30]&(1<<i))]
        state=(ctypes.c_uint8*32).from_buffer_copy(d)
        upload('gp_personality',persona);upload('gp_alliances',allies);upload('gp_request',request)
        state_at=labels['_ng_state']+84;cpu.m[state_at:state_at+32]=d
        oracle.u.mem_write(oracle.base+0x19aa,bytes(d[:30]));oracle.u.mem_write(oracle.base+0x9c,allies);oracle.u.mem_write(oracle.base+0x4a40,persona)
        for at,n in [(0x99f0,f),(0x9a28,0x4a40),(0x2ec6,clock),(0xa0,word(request,16)),(0xa2,word(request,4)),(0xa4,word(request,6)),(0x19cc,word(request,18)),(0x2418,human),(0x2d16,word(request,30)),(0x3098,word(request,10))]:oracle.word(at,n)
        events.clear()
        try:oracle.call(0x16b4,0x2a84,near=True)
        except RuntimeError as error:
            raise RuntimeError((case,'input',d.hex(),'request',request.hex(),'pc',hex(oracle.machine.r('ip'))))from error
        expected=bytearray(oracle.u.mem_read(oracle.base+0x19aa,30))+d[30:]
        if events:expected[30],expected[31]=events[-1]
        groups=bytes(oracle.u.mem_read(oracle.base+0x9c,4));seed=oracle.word(0x3098);mode=oracle.word(0xa0)
        lib.gp_diplomacy_tick(state)
        cpu.m[labels['c_sp']:labels['c_sp']+2]=b'\xff\xc3';cpu.a=state_at&255;cpu.x=state_at>>8;cpu.s=0xfd;cpu.call(labels['_gp_diplomacy_tick'],max_ops=1000000)
        for backend in ['C','6502']:
            actual=bytes(state)if backend=='C'else bytes(cpu.m[state_at:state_at+32])
            req=bytes((ctypes.c_uint8*32).in_dll(lib,'gp_request'))if backend=='C'else bytes(cpu.m[labels['_gp_request']:labels['_gp_request']+32])
            pact=bytes((ctypes.c_uint8*4).in_dll(lib,'gp_alliances'))if backend=='C'else bytes(cpu.m[labels['_gp_alliances']:labels['_gp_alliances']+4])
            if actual!=expected:
                diff=[(i,a,b)for i,(a,b)in enumerate(zip(expected,actual))if a!=b]
                raise AssertionError((backend,case,f,human,'state',diff,'input',d.hex(),'request',request.hex(),'persona',persona.hex()))
            assert pact==groups,(backend,case,'alliances',pact,groups)
            assert word(req,10)==seed,(backend,case,'seed',word(req,10),seed)
            assert word(req,16)==mode,(backend,case,'mode',word(req,16),mode)
        counts['speech']+=bool(events);counts['changed_groups']+=groups!=allies;counts['proposals']+=not word(d,4)and bool(word(expected,4));counts['closed']+=bool(word(d,4))and not word(expected,4);counts['human_input']+=f==human and bool(word(d,6))
    report=dict(scenarios=cases,backends=['host C','native banked NMOS 6502'],original='16B4:2A84',checks=['30-byte negotiation state','alliance groups','PRNG','presentation mode','speech callback ID/speaker'],coverage=counts,exe_sha256=oracle.rules['exe_sha256'])
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dos',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--cases',type=int,default=2048)
    a=p.parse_args();verify(a.dos,a.native,a.out,a.cases)
