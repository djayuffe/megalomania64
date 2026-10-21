"""Read version-checked campaign and rule tables from the owner's DOS EXE.

No original executable or extracted table is distributed with the source.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from intro_timeline import EXE_SHA256

DS_FILE = 0x22f00
SECTORS = 16
SECTOR_BYTES = 0x449
SECTOR_BASE = 0x5560


def extract(data):
    if hashlib.sha256(data).hexdigest() != EXE_SHA256:
        raise ValueError('unsupported gameplay executable')
    def word(offset):return struct.unpack_from('<H',data,DS_FILE+offset)[0]
    def block(offset,length):
        if not 0 <= offset <= 0xffff or offset+length>0x10000:
            raise ValueError('table outside original data segment')
        return data[DS_FILE+offset:DS_FILE+offset+length]
    # Check the operations that establish 16 sectors, 1097-byte records, and
    # the resource scale. Pointer-like bytes alone are not accepted as evidence.
    checks={0x1c574:'8106109a490483060c9a01833e0c9a',
            0x1c5ad:'c706189aac45c706149a924d',
            0x1c668:'33d2bb1900f7e3d1e0',
            0x88c9:'33d2bb0300f7f3a3f099',
            0x14386:'33d28bd8f7e3a1fc99d1e8d1e8d1e8d1e8d1e8'}
    for offset,code in checks.items():
        if data[offset:offset+len(bytes.fromhex(code))] != bytes.fromhex(code):
            raise ValueError(f'gameplay instruction mismatch at {offset:05x}')
    # Independent data/routine checks below and differential x86 tests are the
    # primary authority; reject a different binary before touching its pointers.
    classes=list(block(0x45ac,20))
    if classes != [0]*4+[1]*4+[2]*12:raise ValueError('element class table mismatch')
    islands=[]
    for index in range(28):
        tiles=list(block(0x1e84+index*16,16))
        pointer=word(0x4d92+index*2);cursor=pointer;sectors=[]
        for slot,tile in enumerate(tiles):
            deposits=[]
            if tile and index != 27:
                for element,quanta in struct.iter_unpack('<BB',block(cursor,8)):
                    if element!=255 and element>=20:raise ValueError('invalid element index')
                    deposits.append(dict(element=element,amount=quanta*50))
                cursor+=8
            sectors.append(dict(index=slot,tile=tile,land=bool(tile),deposits=deposits))
        if index<26 and cursor!=word(0x4d92+(index+1)*2):
            raise ValueError('campaign resource boundaries disagree')
        islands.append(dict(index=index,start_age=index//3,max_age=min(9,index//3+3),
                            resource_pointer=pointer,sectors=sectors))
    ranges=[list(struct.unpack('<HH',block(0x45c0+i*4,4)))for i in range(10)]
    patterns=[]
    for kind in range(3):
        ages=[];table=word(0x4624+kind*2)
        for age in range(10):
            pointer=word(table+age*2);count=word(pointer)
            if not 1<=count<=4:raise ValueError('invalid design template')
            requirements=[list(v)for v in struct.iter_unpack('<HH',block(pointer+2,count*4))]
            if any(group>=10 or not 1<=amount<=255 for group,amount in requirements):
                raise ValueError('invalid design requirement')
            ages.append(requirements)
        patterns.append(ages)
    return dict(exe_sha256=EXE_SHA256,islands=islands,element_classes=classes,
                buildings=[dict(health=list(struct.unpack('<10H',block(word(0x4c26+kind*2),20))),
                                turrets=word(0x4b62+kind*2),turret_offset=word(0x2ce4+kind*2))for kind in range(4)],
                army_rules=dict(health=list(struct.unpack('<11H',block(0x4b92,22))),
                                strength=list(struct.unpack('<11H',block(0x4ba8,22))),
                                crew=list(struct.unpack('<11H',block(0x4bd4,22)))),
                defence_rules=dict(health=list(struct.unpack('<10H',block(0x4b6a,20))),
                                   strength=list(struct.unpack('<10H',block(0x4b7e,20))),
                                   crew=list(struct.unpack('<10H',block(0x4bea,20)))),
                material_groups=ranges,design_patterns=patterns,
                speed=list(struct.unpack('<3H',block(0x44,6))),
                task_bases=dict(zip(['tower','building','birth','mining','research','manufacture','gathering'],struct.unpack('<7H',block(0x4594,14)))),
                research_complexity=list(struct.unpack('<7H',block(0x47a8,14))),
                manufacture_complexity=list(struct.unpack('<7H',block(0x4808,14))),
                research_points=list(struct.unpack('<6H',block(0x47ce,12))),
                technology_points=list(struct.unpack('<10H',block(0x47e2,20))),
                dates=list(struct.unpack('<10h',block(0x23bc,20))),
                evidence=dict(sector_initializer='1A17:0964',deposits_file='0x1c590',
                    worker_rate='11B9:11E8',population_tick='11B9:1487',mining_tick='11B9:1678',
                    gathering_reconcile='11B9:108C',gathering_tick='0D24:2336',
                    army_arrival='1A17:165F',army_damage='0000:5E55',turret_damage='0000:6154',
                    army_extract='11B9:1E18',army_return='11B9:1F93',tower_completion='0000:CD19',
                    ownership_install='0000:5A9F',building_removal='0000:670B',
                    research_tick_file='0xdf50',manufacture_tick_file='0xe420'))


def initial_sector(descriptor,classes,age):
    deposits=[];stocks=[0]*20
    for deposit in descriptor['deposits']:
        element,amount=deposit['element'],deposit['amount']
        deposits.append((element if element!=255 else 65535,amount))
        if element != 255 and classes[element]==0:stocks[element]+=amount
    return dict(land=descriptor['land'],owner=4,age=age,deposits=deposits,stocks=stocks)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    if a.out.resolve().is_relative_to(Path(__file__).resolve().parents[1]):p.error('keep original-derived data outside source checkout')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    result=extract(a.exe.read_bytes());a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('Extracted 28 campaign layouts, 20 element classes and 30 design templates:',a.out)
