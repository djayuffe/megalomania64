"""Bounded native world storage: 16 slots of 656 bytes, four ages per island.

No game content is embedded. This stores all fields used by the verified core;
unused DOS rendering fields are regenerated rather than retained.
"""
import struct

SLOT=656
RECORD=0x449

def spans(first,last):
    if not 0<=first<=last<10 or last-first>3:raise ValueError('invalid island ages')
    result=[(10,2)]
    result += [(0x6c+k*24+4,12)for k in range(3)]
    result += [(0xb4,50)]
    result += [(0xe6+k*20+first*2,(last-first+1)*2)for k in range(3)]
    result += [(0x122,18),(0x134,104)]
    result += [(0x19c+k*100+first*10,(last-first+1)*10)for k in range(3)]
    for faction in range(4):
        result += [(0x2c8+faction*11+first,last-first+1),(0x2c8+faction*11+10,1)]
    result += [(0x2f4,20)]
    for base in [0x308,0x360]:
        for faction in range(4):
            result += [(base+faction*22+first*2,(last-first+1)*2),(base+faction*22+20,2)]
    result += [(0x3b8,70),(0x3fe,30),(0x41c,45)]
    return result

def encode(record,first,last):
    if len(record)!=RECORD:raise ValueError('invalid sector size')
    out=bytearray()
    for k in range(4):
        at=12+k*24
        workers=struct.unpack_from('<H',record,at+4)[0]
        deadline=struct.unpack_from('<I',record,at+6)[0]
        rate=struct.unpack_from('<H',record,at+14)[0]
        if deadline not in [0,48000,0xffffffff]:raise ValueError('invalid tower deadline')
        active=deadline==48000
        if active and rate!=workers-workers//32:raise ValueError('invalid tower worker rate')
        out += record[at+4:at+6]+record[at+10:at+14]+bytes([active])
    for at,size in spans(first,last):out+=record[at:at+size]
    if len(out)>SLOT:raise ValueError('sector exceeds slot')
    return bytes(out)+bytes(SLOT-len(out))

def decode(data,first,last):
    if len(data)!=SLOT:raise ValueError('invalid slot size')
    out=bytearray(RECORD);cursor=0
    for k in range(4):
        at=12+k*24;workers=struct.unpack_from('<H',data,cursor)[0]
        active=data[cursor+6]
        if active>1:raise ValueError('invalid tower state')
        out[at+4:at+6]=data[cursor:cursor+2];out[at+10:at+14]=data[cursor+2:cursor+6]
        struct.pack_into('<I',out,at+6,48000 if active else 0xffffffff)
        struct.pack_into('<H',out,at+14,workers-workers//32 if active else 0)
        cursor+=7
    for at,size in spans(first,last):out[at:at+size]=data[cursor:cursor+size];cursor+=size
    if any(data[cursor:]):raise ValueError('nonzero slot padding')
    return out
