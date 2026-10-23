#!/usr/bin/env python3
"""Compare whole-world tactical turns to DOS, host C and banked native 6502.

Requires private owner content and a prior tools/build_native.py output. Disk
loads are modeled only in the CPU audit; VICE verifies the actual loader.
"""
import argparse,ctypes,json,random,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from cpu6502 import CPU
from gameplay_oracle import Oracle
from gameplay_data import SECTOR_BASE,SECTOR_BYTES
from native_world import encode,decode,SLOT

def put(b,at,n):struct.pack_into('<H',b,at,n&65535)
def word(b,at):return struct.unpack_from('<H',b,at)[0]

def verify(dos,native,out,cases=256,fast_setup=False):
    out=out.resolve();native=native.resolve()
    if out.is_relative_to(ROOT):raise ValueError('keep original-derived evidence outside checkout')
    out.mkdir(parents=True,exist_ok=True);(out/'verification.json').unlink(missing_ok=True)
    oracle=Oracle(dos,out/'oracle');rules=oracle.rules;rng=random.Random(0x114f)
    (out/'memory.h').write_text('#include <stdint.h>\nextern uint8_t world_memory[10496];\n')
    (out/'memory.c').write_text('#include <stdint.h>\nuint8_t world_memory[10496];\n')
    cmd=['clang','-shared','-O2','-fPIC','-DWORLD_ADDRESS=world_memory','-include',out/'memory.h',*[ROOT/f'src/gameplay/{n}.c'for n in ['core','ai','tactics','military','strategy','world','game','campaign']],out/'memory.c','-o',out/'game.dylib']
    subprocess.run(list(map(str,cmd)),check=True,capture_output=True);lib=ctypes.CDLL(str(out/'game.dylib'))
    labels={s.lstrip('.'):int(a,16)for _,a,s in [line.split()for line in(native/'runtime.lbl').read_text().splitlines()]}
    cpu=CPU(native/'files/NGHIGH')
    for name in ['NGLOW','NGEXTRA','NGDRAW','NGTEXT']:
        raw=(native/'files'/name).read_bytes();at=word(raw,0);cpu.m[at:at+len(raw)-2]=raw[2:]
    raw=(native/'runtime.bin.aux').read_bytes();cpu.m[0x0800:0x0800+len(raw)]=raw
    raw=(native/'runtime.bin.bank').read_bytes();cpu.m[0xd400:0xd400+len(raw)]=raw;cpu.ram_io[:min(4096,len(raw))]=raw[:4096];cpu.m[1]=0x34
    banks={labels['_gp_ensure_'+name]:(native/f'runtime.bin.{suffix}').read_bytes()for name,suffix in [('rare','rare'),('campaign','camp'),('ai','ai'),('tactics','tactics'),('military','military'),('strategy','strategy')]}
    from unicorn import UC_HOOK_CODE
    dos_draws=[];native_draws=[]
    at=(oracle.machine.module_seg+0x11b9)*16+0xeb1
    oracle.u.hook_add(UC_HOOK_CODE,lambda u,a,s,d:dos_draws.append((oracle.word(0x99f0),oracle.word(0x3098))),None,at,at)
    step=cpu.step
    def bank_step():
        if cpu.pc==labels["_gp_dispatch"] and cpu.m[labels["_gp_request"]]==7:native_draws.append((word(cpu.m,labels["_gp_request"]+2),word(cpu.m,labels["_gp_request"]+10)))
        if cpu.pc in banks:
            raw=banks[cpu.pc];cpu.m[0xef00:0xef00+len(raw)]=raw
            cpu.pc=((cpu.pop()|(cpu.pop()<<8))+1)&65535
        else:step()
    cpu.step=bank_step
    def upload(name,data):
        (ctypes.c_uint8*len(data)).in_dll(lib,name)[:]=data
        at=labels['_'+name]if name!='world_memory'else 0x4000;cpu.m[at:at+len(data)]=data
    def scalar(name,n):
        ctypes.c_uint8.in_dll(lib,name).value=n;cpu.m[labels['_'+name]]=n
    def call(name):
        cpu.m[labels['c_sp']:labels['c_sp']+2]=b'\xff\xc3';cpu.s=0xfd
        cpu.call(labels['_'+name],max_ops=2500000)
    tables={
      'gp_army_rules':struct.pack('<33H',*(rules['army_rules']['health']+rules['army_rules']['strength']+rules['army_rules']['crew'])),
      'gp_buildings':b''.join(struct.pack('<12H',*(v['health']+[v['turrets'],v['turret_offset']]))for v in rules['buildings'])}
    for name,data in tables.items():upload(name,data)
    personas=b''.join(struct.pack('<28H',*p)for p in rules['personalities']);upload('world_personalities',personas)
    counts={n:dict(scenarios=0,actions=0)for n in ['expedition','weak','demobilize','roam']}
    for case in range(cases):
        dos_draws.clear();native_draws.clear()
        routine=['expedition','weak','demobilize','roam'][case%4];counts[routine]['scenarios']+=1
        first,last=[(0,3),(3,6),(6,9),(9,9)][case//4%4];source=rng.randrange(16);f=case//16%4;human=(f+1)%4;active=[3,5,15][case%3]|(1<<f)
        allies=bytearray([1,2,4,8]);ally=(f+2)%4
        if case%5==0:allies[f]|=1<<ally;allies[ally]|=1<<f
        persona=struct.pack('<28H',*rules['personalities'][case//64%4]);seed=rng.randrange(65536);island=27 if case%11==0 else (first*3)
        sectors=[]
        for s in range(16):
            b=bytearray(SECTOR_BYTES);put(b,0xa,65535);put(b,0xbe,65535);put(b,0xd2,65535);b[0x3b8:0x3c2]=bytes([255])*10
            put(b,0x3fe,rng.randrange(5));put(b,0x402,s);put(b,0x418,first);put(b,0x43e,65535);put(b,0x440,65535)
            b[0x448]=128 if rng.randrange(4) else 0
            for age in range(first,last+1):
                put(b,0x10e+age*2,rng.choice([0,0,1,5,20]));put(b,0x126,word(b,0x126)|(1<<age))
                b[0x264+age*10:0x264+age*10+10]=bytes([0,2]+[255,0]*4)
            put(b,0x174,rng.choice([0,10,100,2000]));people=rng.choice([0,10,50,100,250,998]);put(b,0x404,people);put(b,0x406,people)
            for faction in range(4):
                for age in [first,10]:
                    n=rng.choice([0,0,0,1,5,20]);b[0x2c8+faction*11+age]=n
                    put(b,0x2f4+faction*2,word(b,0x2f4+faction*2)+n)
                    strength=n*rules['army_rules']['strength'][age];put(b,0x360+faction*22+age*2,strength)
                    put(b,0x3f4+faction*2,word(b,0x3f4+faction*2)+strength)
                    put(b,0x308+faction*22+age*2,rules['army_rules']['health'][age]if n else 0)
            if s==source:
                put(b,0x3fe,f);b[0x448]=128;put(b,0x3d6,[1,14,100][case//4%3])
                if routine=='roam':put(b,0x3fe,[4,f,(f+2)%4][case//4%3])
                if routine in ['roam','demobilize'] and case//4%2==0:
                    for other in range(4):
                        if other==f:continue
                        b[0x2c8+other*11:0x2c8+other*11+11]=bytes(11);put(b,0x2f4+other*2,0);put(b,0x3f4+other*2,0)
                        b[0x308+other*22:0x308+other*22+22]=bytes(22);b[0x360+other*22:0x360+other*22+22]=bytes(22)
            sectors.append(decode(encode(b,first,last),first,last))
        # Sparse fixtures guarantee successful field movement, including
        # retreat from an undefended enemy tower and mixed air/ground forces.
        if routine=='roam' and case//4%4==0:
            target=source^1
            for s,b in enumerate(sectors):
                b[0x2c8:0x3b8]=bytes(0xf0);b[0x448]=128 if s in [source,target]else 0
                put(b,0x3fe,4);put(b,0x3f4,0);put(b,0x3f6,0);put(b,0x3f8,0);put(b,0x3fa,0)
            b=sectors[source];put(b,0x3fe,(f+2)%4 if case//16%2 else 4)
            b[0x2c8+f*11+10]=30;put(b,0x2f4+f*2,30)
            strength=30*rules['army_rules']['strength'][10];put(b,0x360+f*22+20,strength);put(b,0x3f4+f*2,strength)
            put(b,0x308+f*22+20,rules['army_rules']['health'][10])
            if first<=6<=last and word(b,0x3fe)==4:
                b[0x2c8+f*11+6]=5;put(b,0x2f4+f*2,35)
                strength=5*rules['army_rules']['strength'][6];put(b,0x360+f*22+12,strength);put(b,0x3f4+f*2,word(b,0x3f4+f*2)+strength)
                put(b,0x308+f*22+12,rules['army_rules']['health'][6])
            put(sectors[target],0x3fe,f)
        state=bytearray(128);state[12]=island;state[13]=human;state[14]=active;put(state,26,seed);state[82]=255
        compact=b''.join(encode(b,first,last)for b in sectors)
        upload('ng_terrain',bytes(1 if b[0x448]&128 else 0 for b in sectors));upload('ng_state',state);upload('gp_alliances',allies);upload('gp_personality',persona);upload('world_memory',compact)
        scalar('world_first',first);scalar('world_last',last)
        for s,b in enumerate(sectors):
            (ctypes.c_uint8*SECTOR_BYTES).in_dll(lib,'gp_sector')[:]=b
            ctypes.c_uint8.in_dll(lib,'world_slot').value=s;lib.ng_cache()
            if not fast_setup:
                at=labels['_gp_sector'];cpu.m[at:at+SECTOR_BYTES]=b;cpu.m[labels['_world_slot']]=s;call('ng_cache')
        if fast_setup:
            # Fixture construction is not the routine under audit. Inject the
            # same independent Python-derived cache into both backends; the
            # real routine's world_get/put and post-action cache still execute.
            for name,data in [
                ('ng_owners',bytes(255 if b[0x448]&64 else word(b,0x3fe)for b in sectors)),
                ('ng_ruined',bytes(bool(b[0x448]&64)for b in sectors)),
                ('ng_ages',bytes(word(b,0x418)for b in sectors)),
                ('ng_people',struct.pack('<16H',*(word(b,0x404)for b in sectors))),
                ('ng_units',struct.pack('<64H',*(word(b,0x2f4+f*2)for b in sectors for f in range(4)))),
                ('ng_strength',struct.pack('<64H',*(word(b,0x3f4+f*2)for b in sectors for f in range(4))))]:upload(name,data)
        scalar('world_slot',source);lib.world_get()
        if fast_setup:
            at=labels['_gp_sector'];cpu.m[at:at+SECTOR_BYTES]=sectors[source]
        else:call('world_get')
        # Initialize the complete DOS sector table and explicitly reset globals.
        for s,b in enumerate(sectors):
            oracle.u.mem_write(oracle.base+SECTOR_BASE+s*SECTOR_BYTES,bytes(b));oracle.word(0x553e+s*2,SECTOR_BASE+s*SECTOR_BYTES)
        for at,n in [(0x555e,SECTOR_BASE),(0x9a10,SECTOR_BASE+source*SECTOR_BYTES),(0x1c64,island),(0x1c6c,first),(0x1c6e,last),(0x2d16,active),(0x3098,seed),(0x2418,human),(0x1c78,0),(0x1c74,1),(0x2456,0),(0x9a28,0x4a40),(0x19cc,0),(0x19c8,0),(0xa0,0)]:oracle.word(at,n)
        oracle.u.mem_write(oracle.base+0x550a,bytes(36));oracle.u.mem_write(oracle.base+0x9c,bytes(allies));oracle.u.mem_write(oracle.base+0x4a40,persona)
        kind=0
        for faction in [0,2,1,3]:
            if faction==human:continue
            oracle.word(0x2d28+faction*2,0x4a40+kind*56);kind+=1
        oracle.word(0x2d28+human*2,0x4a40+3*56)
        if routine=='roam':oracle.u.mem_write(oracle.base+0x4a40,personas)
        entry={'expedition':0x114f,'weak':0xfb2,'demobilize':0x142a,'roam':0x228}[routine]
        oracle.call(0x16b4,entry,near=True);expected_result=oracle.word(0x99f0);expected_seed=oracle.word(0x3098)
        expected=[]
        for s in range(16):
            b=bytearray(oracle.u.mem_read(oracle.base+SECTOR_BASE+s*SECTOR_BYTES,SECTOR_BYTES))
            origin=word(b,0x440)
            if b[0x444]and SECTOR_BASE<=origin<SECTOR_BASE+16*SECTOR_BYTES:put(b,0x440,(origin-SECTOR_BASE)//SECTOR_BYTES)
            expected.append(encode(b,first,last))
        if routine in ['weak','demobilize']:
            part=int(routine=='demobilize');result=lib.ng_demobilize(part);cpu.a=part;call('ng_demobilize')
        else:
            name='ng_'+routine;result=getattr(lib,name)();call(name)
        native_result=cpu.a;lib.ng_cache();call('ng_cache');counts[routine]['actions']+=bool(expected_result)
        for backend in ['C','6502']:
            actual=bytes((ctypes.c_uint8*(16*SLOT)).in_dll(lib,'world_memory'))if backend=='C'else bytes(cpu.m[0x4000:0x6900])
            actual_state=bytes((ctypes.c_uint8*128).in_dll(lib,'ng_state'))if backend=='C'else bytes(cpu.m[labels['_ng_state']:labels['_ng_state']+128])
            actual_result=result if backend=='C'else native_result
            if actual!=b''.join(expected):
                differences=[(i//SLOT,i%SLOT,x,y)for i,(x,y)in enumerate(zip(b''.join(expected),actual))if x!=y]
                raise AssertionError(f'{backend}: case {case}, source {source}, ages {first}..{last}, seed {seed}, island {island}: {differences[:12]}')
            assert actual_result==expected_result,(backend,routine,case,'result',actual_result,expected_result)
            if routine=='roam':assert actual_state[39]==oracle.word(0x19c8),(backend,case,'roaming cooldown')
            assert word(actual_state,26)==expected_seed,(backend,case,'seed',word(actual_state,26),expected_seed,'DOS draws',dos_draws,'native draws',native_draws)
        if (case+1)%32==0:print(f'Verified {case+1}/{cases} whole-world cases',flush=True)
    report=dict(scenarios=cases,backends=['host C','native banked NMOS 6502'],original='16B4:114F expedition, 0FB2/142A demobilization, 0228 roaming',routines=counts,world_records_per_scenario=16,fixture_setup='direct identical cache injection'if fast_setup else'native cache/codec execution',exe_sha256=rules['exe_sha256'])
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dos',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--cases',type=int,default=256)
    p.add_argument('--fast-setup',action='store_true',help='inject fixture caches; still execute all audited routine world and cache mutations')
    a=p.parse_args();verify(a.dos,a.native,a.out,a.cases,a.fast_setup)
