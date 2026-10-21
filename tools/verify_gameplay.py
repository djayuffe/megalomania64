#!/usr/bin/env python3
"""Compare the gameplay C/6502 translations against callable original x86 code.

Requires the owner's audited DOS files, optional Unicorn, a cc65 source/build
root, and a host C compiler. Writes original-derived evidence outside the repo.
"""
import argparse
import ctypes
import json
import random
import struct
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from cpu6502 import CPU
from gameplay_data import extract,initial_sector,SECTOR_BYTES,SECTOR_BASE
from gameplay_oracle import Oracle


def put(buf,at,value):struct.pack_into('<H',buf,at,value&65535)
def put32(buf,at,value):struct.pack_into('<I',buf,at,value&0xffffffff)
def get(buf,at):return struct.unpack_from('<H',buf,at)[0]


def build(cc65,out):
    cc65=cc65.resolve();out.mkdir(parents=True,exist_ok=True)
    def run(args):
        result=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    run([cc65/'bin/cc65','-t','none','-O','-Cl','-o',out/'core.s',ROOT/'src/gameplay/core.c'])
    for name,source in [('core',out/'core.s'),('entry',ROOT/'src/gameplay/entry.s')]:
        run([cc65/'bin/ca65','-t','none','-o',out/(name+'.o'),source])
    run([cc65/'bin/ld65','-C',ROOT/'src/gameplay/core.cfg','-m',out/'core.map','-Ln',out/'core.lbl','-o',out/'core.bin',out/'core.o',out/'entry.o',cc65/'lib/none.lib'])
    run(['clang','-O2','-shared','-fPIC','-o',out/'core.dylib',ROOT/'src/gameplay/core.c'])
    (out/'core.prg').write_bytes(b'\x00\x80'+(out/'core.bin').read_bytes())
    (out/'core-low.prg').write_bytes(b'\x00\x10'+(out/'core.bin.low').read_bytes())
    labels={line.split()[2].lstrip('.'):int(line.split()[1],16) for line in (out/'core.lbl').read_text().splitlines() if line.startswith('al ')}
    return labels


def verify(dos,cc65,out):
    out=out.resolve()
    if out.is_relative_to(ROOT):raise ValueError('keep original-derived evidence outside checkout')
    (out/'verification.json').unlink(missing_ok=True)
    rules=extract((dos/'MEGA.EXE').read_bytes());oracle=Oracle(dos,out/'oracle')
    labels=build(cc65,out);lib=ctypes.CDLL(str((out/'core.dylib').resolve()))
    native=CPU(out/'core.prg');rng=random.Random(0x1991)
    low=(out/'core.bin.low').read_bytes();native.m[0x1000:0x1000+len(low)]=low
    bank=(out/'core.bin.bank').read_bytes();native.m[0xd400:0xd400+len(bank)]=bank
    native.m[1]=0x34
    classes=bytes(rules['element_classes'])
    buildings=b''.join(struct.pack('<12H',*(v['health']+[v['turrets'],v['turret_offset']]))for v in rules['buildings'])
    patterns=b''.join(bytes([len(pattern)]+[v for pair in pattern for v in pair]+[0]*(8-len(pattern)*2))for group in rules['design_patterns']for pattern in group)
    groups=bytes(v for pair in rules['material_groups']for v in pair)
    complexity=struct.pack('<7H',*rules['research_complexity'])
    manufacture=struct.pack('<7H',*rules['manufacture_complexity'])
    research_points=struct.pack('<6H',*rules['research_points'])
    technology_points=struct.pack('<10H',*rules['technology_points'])
    army_rules=struct.pack('<33H',*(rules['army_rules']['health']+rules['army_rules']['strength']+rules['army_rules']['crew']))
    defence_rules=struct.pack('<30H',*(rules['defence_rules']['health']+rules['defence_rules']['strength']+rules['defence_rules']['crew']))
    tested=0;per_op={}
    def check(op,sector,a=0,b=0,c=0,recipe=None,seed=0,base=0,scale=0,run=0,human=0,max_age=9,army=None,alliances=None,active=15,origin=0):
        nonlocal tested
        request=bytearray(32);request[0]=op
        for offset,value in [(2,a),(4,b),(6,c),(8,run),(10,seed),(14,base),(16,scale),(24,origin),(26,human),(28,max_age),(30,active)]:put(request,offset,value)
        recipe=recipe or bytes([255,0])*5
        army=army or bytes(11);alliances=alliances or bytes([1,2,4,8])
        expected,value,endseed,hi,rate=oracle.apply(op,sector,request,recipe,army,alliances)
        for prefix,data in [('gp_sector',sector),('gp_request',request),('gp_recipe',recipe),('gp_classes',classes),('gp_buildings',buildings),('gp_patterns',patterns),('gp_groups',groups),('gp_complexity',complexity),('gp_manufacture',manufacture),('gp_research_points',research_points),('gp_technology_points',technology_points),('gp_army',army),('gp_army_rules',army_rules),('gp_defence_rules',defence_rules),('gp_alliances',alliances),('gp_combat_rules',struct.pack('<5H',*rules['combat_rules']))]:
            arr=(ctypes.c_uint8*len(data)).in_dll(lib,prefix);arr[:]=data
            addr=labels['_'+prefix];native.m[addr:addr+len(data)]=data
        lib.gp_dispatch()
        native.call(labels['gp_run'],max_ops=2000000)
        for backend in ['C','6502']:
            if backend=='C':
                actual=bytes((ctypes.c_uint8*SECTOR_BYTES).in_dll(lib,'gp_sector'))
                req=bytes((ctypes.c_uint8*32).in_dll(lib,'gp_request'))
            else:
                addr=labels['_gp_sector'];actual=bytes(native.m[addr:addr+SECTOR_BYTES])
                addr=labels['_gp_request'];req=bytes(native.m[addr:addr+32])
            if actual!=expected:
                differences=[(hex(i),x,y)for i,(x,y)in enumerate(zip(expected,actual))if x!=y]
                raise AssertionError(f'{backend}, op {op}, a={a}, b={b}, c={c}: sector differs: {differences[:12]}')
            if op in [4,5,7,12,18,24,25,28,34] and get(req,12)!=value:
                raise AssertionError(f'{backend}, op {op}, a={a}, seed={seed}: result {get(req,12)} != original {value}')
            if op in [7,17,20,24,25,33,34,35] and get(req,10)!=endseed:raise AssertionError(f'{backend}: PRNG seed differs')
            if op in [20,28,29,30,31]:
                if backend=='C':actual_army=bytes((ctypes.c_uint8*11).in_dll(lib,'gp_army'))
                else:actual_army=bytes(native.m[labels['_gp_army']:labels['_gp_army']+11])
                if actual_army!=oracle.army:raise AssertionError(f'{backend}: unaccepted army differs')
                if op==20 and not army[8] and not sector[0x448]&64 and get(req,12)!=oracle.army_left:
                    raise AssertionError(f'{backend}: unaccepted unit count differs')
            if op==12:
                if backend=='C':actual_recipe=bytes((ctypes.c_uint8*10).in_dll(lib,'gp_recipe'))
                else:actual_recipe=bytes(native.m[labels['_gp_recipe']:labels['_gp_recipe']+10])
                if actual_recipe!=oracle.recipe or get(req,10)!=endseed or get(req,18)!=hi:
                    raise AssertionError(f'{backend}: recipe, PRNG or substitution differs: {actual_recipe.hex()} != {oracle.recipe.hex()}, seed {get(req,10)} != {endseed}, variant {get(req,18)} != {hi}')
            if op==8 and (get(req,12)!=rate or struct.unpack_from('<I',req,22)[0]!=(hi<<16|value)):
                raise AssertionError(f'{backend}: task rate/deadline differ')
        tested+=1;per_op[op]=per_op.get(op,0)+1
        return bytearray(expected)
    # All 448 campaign sectors are compared to the executed original initializer.
    for island in rules['islands']:
        original=oracle.initialize(island['index'])
        for desc,sector in zip(island['sectors'],original):
            expected=initial_sector(desc,rules['element_classes'],island['start_age'])
            assert bool(sector[0x448]&128)==expected['land']
            assert get(sector,0x3fe)==4 and get(sector,0x418)==expected['age']
            assert list(struct.unpack_from('<20H',sector,0x174))==expected['stocks']
            if island['index']!=27 and desc['land']:
                actual=[(get(sector,0x140+j*16),get(sector,0x142+j*16))for j in range(4)]
                assert actual==(expected['deposits'] or [(65535,0)]*4),(island['index'],desc['index'],actual,expected['deposits'])
    # Reinitialize so repeated event calls see a valid original campaign state.
    oracle.initialize(0)
    clean=bytearray(SECTOR_BYTES)
    for free in [0,1,2,30,31,32,99,100,498,499,500,997]:
        check(0,clean,a=free)
    for free in [1,10,31,32,100,498,499]:
        sector=bytearray(SECTOR_BYTES);put(sector,0x404,min(998,free+10));put(sector,0x406,free)
        put32(sector,0xb4,6000);n=free+1 if free+1<500 else 0;put(sector,0xbc,n-n//32)
        for progress in [0,5999,6000,12001]:
            put32(sector,0xb8,progress)
            check(1,sector,a=250)
    for slot in range(4):
        sector=bytearray(SECTOR_BYTES);put(sector,0x406,100);d=0x134+slot*16
        put(sector,d,2);put(sector,d+12,4+slot);put(sector,d+14,200);put32(sector,d+6,1000)
        for workers in [0,1,31,32,90]:check(2,sector,a=workers,b=slot)
    for element in [0,4,7,8,19]:
        for remaining in [1,2,40]:
            sector=bytearray(SECTOR_BYTES);put(sector,0x406,90);d=0x134
            for j in range(4):put(sector,d+j*16+12,65535);put32(sector,d+j*16+2,0xffffffff)
            put(sector,d,10);put32(sector,d+2,3000);put(sector,d+10,10);put(sector,d+12,element);put(sector,d+14,remaining)
            for elapsed in [1,299,300,900,14000]:check(3,sector,a=elapsed)
    for i in range(60):
        sector=bytearray(SECTOR_BYTES);recipe=bytearray([255,0]*5)
        for e in range(20):put(sector,0x174+2*e,rng.randrange(1000))
        for j,e in enumerate(rng.sample(range(20),rng.randrange(1,6))):recipe[j*2:j*2+2]=bytes([e,rng.randrange(1,16)])
        check(4,sector,recipe=recipe)
        check(5,sector,a=rng.randrange(1,70),recipe=recipe)
    for count in [0,1,10,200,300]:
        sector=bytearray(SECTOR_BYTES)
        for kind in range(3):
            for age in [0,3,9]:check(6,sector,a=count,b=kind,c=age)
    for bound in [0,1,2,3,4,10,31,32,100,256,1000,65535]:
        for seed in [0,1,0xffff,12345]:check(7,clean,a=bound,seed=seed)
    for workers in [0,1,31,32,100,998]:
        for base in [4,5,10,15,25,40,80]:check(8,clean,a=workers,base=base,scale=100)
    for element in range(20):
        for age in [0,1,3,9]:
            for mine in [0,2]:
                for remaining,stock in [(0,0),(0,30),(100,0),(100,30)]:
                    sector=bytearray([0xa5]*SECTOR_BYTES)
                    put(sector,0x418,age);sector[0x446]=mine
                    for slot in range(4):
                        put(sector,0x140+slot*16,element if slot==element%4 else 65535)
                        put(sector,0x142+slot*16,remaining)
                    put(sector,0x174+element*2,stock)
                    check(9,sector)
    for kind in [1,2,3]:
        sector=bytearray(SECTOR_BYTES);put(sector,0x406,100)
        d=0x6c+(kind-1)*24;put(sector,d+4,10);put32(sector,d+10,12345)
        for workers in [0,1,31,32,90]:check(10,sector,a=workers,b=kind)
    for age in range(10):
        for elapsed in [0,1,200,50000]:
            sector=bytearray(SECTOR_BYTES);put(sector,0x418,age);put(sector,0x406,20)
            for kind in [1,2,3]:
                d=0x6c+(kind-1)*24
                put(sector,d+4,kind*10);put32(sector,d+6,24000)
                put32(sector,d+10,kind*7900);put(sector,d+14,kind*10)
            check(11,sector,a=elapsed)
    for category in range(3):
        for age in range(10):
            for case in range(12):
                sector=bytearray(SECTOR_BYTES);put(sector,0x418,max(0,age-3))
                for element in range(20):
                    stock=100 if case==0 else (0 if case==1 else rng.choice([0,0,1,2,4,8,16,32]))
                    put(sector,0x174+element*2,stock)
                check(12,sector,b=category,c=age,seed=rng.randrange(65536))
    for category in range(3):
        for age in range(10):
            for same in [False,True]:
                for known in [False,True]:
                    sector=bytearray(SECTOR_BYTES);put(sector,0x418,max(0,age-3))
                    put(sector,0x406,100);put(sector,0xd2,category if same else 65535)
                    put(sector,0xd4,age);put(sector,0xd8,5);put32(sector,0xde,1234)
                    put(sector,0x122+category*2,(1<<age)if known else 0)
                    check(13,sector,a=12,b=category,c=age,run=3)
    for category in range(3):
        for age in [0,4,6,9]:
            for owner in [0,1]:
                for case in range(12):
                    sector=bytearray(SECTOR_BYTES);put(sector,0x418,max(0,age-3))
                    put(sector,0x3fe,owner);put(sector,0x406,40)
                    put(sector,0xd2,category);put(sector,0xd4,age);put(sector,0xd8,20)
                    put(sector,0xd6,[0,1,3][case%3]);put32(sector,0xda,9000)
                    put32(sector,0xde,[0,1,8999][case%3]);put(sector,0xe2,20)
                    put(sector,0x122+category*2,0 if case==8 else 1<<age)
                    put(sector,0x42a+category*2,0 if case==7 else 1<<age)
                    put(sector,0xe4,1 if case>=10 else 0)
                    put(sector,0x174,0 if case in [3,4,5] else 10)
                    recipe=bytes([0,2,255,0,255,0,255,0,255,0])
                    sector[0x19c+category*100+age*10:0x19c+category*100+age*10+10]=recipe
                    check(14,sector,a=[0,1,450,2000][case%4])
    for current in range(10):
        for damage in [0,1,2,3]:
            sector=bytearray(SECTOR_BYTES);put(sector,0x418,current);sector[0x446]=15
            for kind in range(4):put(sector,0x3d6+kind*2,rules['buildings'][kind]['health'][current]*damage//3)
            check(16,sector)
    for current in range(10):
        for category in range(3):
            for case in range(12):
                sector=bytearray(SECTOR_BYTES);age=min(9,current+case%4)
                put(sector,0x418,current);put(sector,0x406,40)
                put(sector,0xbe,category);put(sector,0xc0,age);put(sector,0xc4,20)
                put32(sector,0xc6,15000);put32(sector,0xca,14990)
                put(sector,0xce,20);put(sector,0xd0,case%2)
                put(sector,0x422+category*2,(1<<age)if case%2 else 0);put(sector,0x428,1)
                put(sector,0x12e+category*2,(1<<age)if case==5 else 0)
                put(sector,0x41a,[0,2,6][case%3]);sector[0x446]=15
                if case==10:sector[0x448]=16
                for kind in range(4):put(sector,0x3d6+kind*2,rules['buildings'][kind]['health'][current]//2)
                check(15,sector,a=0 if case==9 else 200,max_age=current if case==11 else 9)
    for category in range(3):
        for age in range(10):
            for case in range(8):
                sector=bytearray(SECTOR_BYTES);put(sector,0x418,max(0,age-3));put(sector,0x406,100)
                put(sector,0xbe,category if case==7 else 65535);put(sector,0xc0,age)
                put(sector,0xc4,5);put(sector,0xc2,20);put32(sector,0xca,1234)
                for element in range(20):put(sector,0x174+element*2,100 if case==0 else rng.choice([0,0,2,8,16]))
                check(17,sector,a=20,b=category,c=age,seed=rng.randrange(65536))
    for age in range(11):
        for count in [0,1,2,25,250]:
            army=bytearray(11);army[age]=count
            check(18,clean,army=army)
    for faction in range(4):
        for age in range(11):
            sector=bytearray(SECTOR_BYTES)
            sector[0x2c8+faction*11+age]=2;put(sector,0x2f4+faction*2,2)
            power=rules['army_rules']['strength'][age]
            put(sector,0x3f4+faction*2,power*2);put(sector,0x360+faction*22+age*2,power*2)
            check(19,sector,b=faction,c=age)
    for faction in range(4):
        for count in [0,1,240,249,250]:
            for mixed in [False,True]:
                sector=bytearray(SECTOR_BYTES);put(sector,0x3fe,0);put(sector,0xa,65535)
                put(sector,0x2f4+faction*2,count);sector[0x2c8+faction*11]=count
                army=bytearray([0]*11);army[0]=20;army[10]=10
                if mixed:army[9]=3;army[6]=5;army[4]=7
                check(20,sector,a=faction,army=army)
    for active in [0,1,3,15]:
        for contenders in [0,1,2,3,5,8,15]:
            for allied in [False,True]:
                sector=bytearray(SECTOR_BYTES);put(sector,0x3fe,4);put(sector,0xa,1)
                for faction in range(4):
                    if contenders&(1<<faction):put(sector,0x2f4+faction*2,10);sector[0x2c8+faction*11+10]=10
                check(21,sector,active=active,alliances=bytes([3,3,4,8])if allied else None)
    for faction in range(4):
        for blocked in [0,1,2]:
            sector=bytearray(SECTOR_BYTES);put(sector,0x3fe,0);put(sector,0xa,65535)
            if blocked==1:sector[0x444]=23
            if blocked==2:sector[0x448]=64
            army=bytearray(11);army[8]=1
            check(20,sector,a=faction,army=army,seed=1991,origin=7)
    for building in range(4):
        for slot in range(rules['buildings'][building]['turrets']):
            for age in range(10):
                for replace in [False,True]:
                    sector=bytearray(SECTOR_BYTES);put(sector,0x3fe,2);put(sector,0x404,100)
                    location=rules['buildings'][building]['turret_offset']+slot
                    sector[location]=0 if replace else 255
                    sector=check(22,sector,a=slot,b=building,c=age)
                    check(23,sector,a=slot,b=building)
    for attacker in range(4):
        for case in range(20):
            sector=bytearray(SECTOR_BYTES)
            for faction in range(4):
                total=0;power=0
                for age in [0,2,4,6,9,10]:
                    count=rng.randrange(4);total+=count
                    sector[0x2c8+faction*11+age]=count
                    hp=rules['army_rules']['health'][age]
                    put(sector,0x308+faction*22+age*2,max(1,hp//2))
                    strength=rules['army_rules']['strength'][age]*count;power+=strength
                    put(sector,0x360+faction*22+age*2,strength)
                put(sector,0x2f4+faction*2,total);put(sector,0x3f4+faction*2,power)
            check(24,sector,a=[0,1,10,100,1000][case%5],b=attacker,c=0,seed=rng.randrange(65536),
                  alliances=bytes([3,3,4,8])if case%2 else None)
    for owner in range(5):
        for case in range(12):
            sector=bytearray(SECTOR_BYTES);put(sector,0x3fe,owner);put(sector,0x404,100)
            sector[0x3b8:0x3c2]=bytes([255]*10)
            if case==10:sector[0x448]=32
            for building in range(4):
                for slot in range(rules['buildings'][building]['turrets']):
                    if (slot+building+case)%3:sector=check(22,sector,a=slot,b=building,c=(building+case)%10)
            check(25,sector,a=[0,1,30,300][case%4],b=case%4,seed=rng.randrange(65536))
    for element in [0,1,2,3,4,8]:
        for stock,left in [(0,0),(0,100),(20,100),(100,100),(120,100),(121,100),(140,100),(141,100),(200,1)]:
            sector=bytearray(SECTOR_BYTES)
            for slot in range(4):put(sector,0x140+slot*16,65535)
            put(sector,0x140,element);put(sector,0x142,left);put(sector,0x174+element*2,stock)
            put32(sector,0x136,2400 if left else 0xffffffff)
            put32(sector,0x13a,1234);put(sector,0x13e,126 if left else 0)
            sector=check(26,sector)
            for elapsed in [0,1,25,1000]:check(27,sector,a=elapsed)
    for faction in range(4):
        for case in range(12):
            sector=bytearray(SECTOR_BYTES);put(sector,0x3fe,4);put(sector,0xa,65535)
            put(sector,0x404,[0,100,990,998][case%4]);put(sector,0x406,[0,50,400][case%3])
            total=0;power=0;army=bytearray(11)
            for age in [0,4,6,9,10]:
                count=rng.randrange(1,12);army[age]=count;total+=count
                sector[0x2c8+faction*11+age]=count
                strength=count*rules['army_rules']['strength'][age];power+=strength
                put(sector,0x360+faction*22+age*2,strength)
                put(sector,0x308+faction*22+age*2,rules['army_rules']['health'][age])
                if age<10:put(sector,0x10e+age*2,199 if case%2 else 0)
            put(sector,0x2f4+faction*2,total);put(sector,0x3f4+faction*2,power)
            check(28,sector,a=faction)
            check(29,sector,army=army)
            check(30,sector,a=faction)
    for faction in range(4):
        for age in range(10):
            for elapsed in [0,1,1000,5000]:
                sector=bytearray(oracle.initialize(min(age*3,27))[6])
                put(sector,0x418,age);put(sector,0x3fe,4);put(sector,0xa,faction)
                d=12+faction*24
                put(sector,d+4,10);put32(sector,d+6,48000);put32(sector,d+10,47990);put(sector,d+14,10)
                sector[0x2c8+faction*11+10]=10;put(sector,0x2f4+faction*2,10)
                put(sector,0x308+faction*22+20,rules['army_rules']['health'][10])
                put(sector,0x360+faction*22+20,10);put(sector,0x3f4+faction*2,10)
                check(31,sector,a=elapsed)
    for kind in range(4):
        for case in range(12):
            sector=bytearray(SECTOR_BYTES);put(sector,0x3fe,case%4);put(sector,0x404,200);put(sector,0x406,50)
            sector[0x446]=15;sector[0x447]=15;put(sector,0x2fc,4)
            sector[0x3b8:0x3c2]=bytes([255]*10)
            for building in range(4):
                for slot in range(rules['buildings'][building]['turrets']):
                    sector=check(22,sector,a=slot,b=building,c=case%10)
            for slot,element in enumerate([0,4,8,19]):
                d=0x134+slot*16;put(sector,d,5);put(sector,d+12,element);put(sector,d+14,100)
                put32(sector,d+2,0xffffffff if case==9 else 3000);put32(sector,d+6,1234);put(sector,d+10,5)
            put(sector,0xbe,65535 if case==10 else 2);put(sector,0xc0,case%10);put(sector,0xc4,20)
            put32(sector,0xc6,15000);put32(sector,0xca,1234);put(sector,0xce,20)
            put(sector,0xd2,65535 if case==11 else 2);put(sector,0xd4,case%10);put(sector,0xd8,30)
            put32(sector,0xda,9000);put32(sector,0xde,1234);put(sector,0xe2,30);put(sector,0xe4,1)
            check(32,sector,b=kind)
    # A persistent Aloha sector: allocate inventors, finish an actual design,
    # then pay for and inventory an early-age weapon. Every step passes through
    # both native backends and is compared with the executed original code.
    sector=bytearray(oracle.initialize(0)[6]);put(sector,0x3fe,0);put(sector,0x404,100)
    sector=check(0,sector,a=100)
    sector=check(17,sector,a=20,b=2,c=0,seed=1991)
    for tick in range(40):
        sector=check(1,sector,a=25)
        sector=check(15,sector,a=25,max_age=3)
        sector=check(9,sector)
    assert get(sector,0x122+2*2)&1,'Aloha design did not complete'
    recipe=sector[0x19c+200:0x19c+210]
    stocks_before=bytes(sector[0x174:0x19c])
    sector=check(5,sector,a=1,recipe=recipe)
    assert bytes(sector[0x174:0x19c])!=stocks_before,'Aloha weapon cost was not paid'
    sector=check(6,sector,a=1,b=2,c=0)
    assert get(sector,0xe6+40)==1,'Aloha weapon was not inventoried'
    # Neutral occupation is contested, then resumed after the hostile army
    # is defeated. Arrival never directly changes tower ownership.
    sector=bytearray(oracle.initialize(0)[6])
    army=bytearray(11);army[0]=10
    sector=check(20,sector,a=1,army=army)
    assert get(sector,0xa)==1 and get(sector,0x3fe)==4
    army=bytearray(11);army[10]=5
    sector=check(20,sector,a=2,army=army)
    assert get(sector,0xa)==65535,'Enemy occupation did not contest construction'
    sector=check(24,sector,a=1000,b=1,c=0,max_age=3,seed=1991)
    assert get(sector,0x2f8)==0,'Hostile army survived the chained damage scenario'
    sector=check(21,sector)
    assert get(sector,0xa)==1 and get(sector,0x3fe)==4,'Construction did not resume on neutral land'
    sector=check(31,sector,a=5000)
    assert get(sector,0x3fe)==1 and sector[0x446]&1,'Completed tower did not claim the sector'
    assert get(sector,0x2f6)==0 and get(sector,0x404)==9,'Tower army was not demobilized correctly'
    # Full scheduler, facility targeting and tower-loss arithmetic. Start from
    # legal records and use the original arrival/ownership routines to construct
    # strength caches instead of inventing inconsistent sector state.
    for age in [0,3,6,9]:
        base=bytearray(oracle.initialize(age*3 if age<9 else 27)[6])
        put(base,0x418,age);put(base,0x3fe,4);base[0x448]=128
        for k in range(4):
            put(base,0x2f4+k*2,0);put(base,0x3f4+k*2,0)
        army=bytearray(11);army[10]=100
        base=check(20,base,a=0,army=army,max_age=9)
        base=check(31,base,a=1000,max_age=9)
        for faction in [0,1,2]:
            army=bytearray(11);army[age if age!=8 else 7]=5+faction;army[10]=10+faction
            base=check(20,base,a=faction,army=army,max_age=9)
        for elapsed in [0,1,3,10,47,99]:
            for seed in [0,1,1991,65535]:
                check(33,base,a=elapsed,c=0,seed=seed,max_age=9,origin=27 if age==9 else 0)
        for damage in [0,1,17,199,200,201,1000]:
            for seed in [0,5,65535]:check(34,base,a=damage,b=1,seed=seed,max_age=9)
        check(35,base,a=1,max_age=9)
    for age in range(10):
        base=bytearray(oracle.initialize(min(age*3,27))[6])
        put(base,0x3fe,0);base[0x446]=1;base[0x448]=128
        base[0x3b8:0x3c2]=bytes([255])*10
        base=check(22,base,a=0,b=0,c=age)
        check(36,base,a=0,b=0)
        army=bytearray(11);army[age if age!=8 else 7]=3;army[10]=5
        base=check(20,base,a=1,army=army)
        check(37,base,a=1,human=3)
    report=dict(exe_sha256=rules['exe_sha256'],campaign_sectors_verified=448,
                scenarios=tested,backends=['host C','native NMOS 6502'],per_opcode=per_op,
                native_code_bytes=(out/'core.bin').stat().st_size+(out/'core.bin.low').stat().st_size+(out/'core.bin.bank').stat().st_size,
                native_code_regions={'0x1000':(out/'core.bin.low').stat().st_size,'0x8000':(out/'core.bin').stat().st_size,'0xd400':(out/'core.bin.bank').stat().st_size},
                chained_scenarios=['Aloha inventors, birth ticks, research completion, resource payment, weapon inventory',
                                  'Neutral occupation, contested construction, hostile army defeated, tower completes and installs owner'],
                source='Audited original DOS near/far routines; complete sector bytes compared',
                limitations=['C64 AI, interface and campaign allocation are native adaptations',
                             'arrival optional DOS global 0x1c78 branch not translated; verified with zero',
                             'future shutdown special branches are not covered by DOS comparisons',
                             'rule comparisons do not establish human balance across all islands'])
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dos',type=Path,required=True);p.add_argument('--cc65',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.resolve().is_relative_to(ROOT):p.error('keep original-derived evidence outside checkout')
    verify(a.dos,a.cc65,a.out)
