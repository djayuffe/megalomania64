#!/usr/bin/env python3
"""Verify the original EXE's M-variant filename table and sunrise palette copy.

This is a version-specific static evidence probe, not an x86 emulator. It fails
if the exact instruction bytes or resource pointers differ from the audited EXE.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def inspect(data):
    if len(data)<0x28000 or data[:2]!=b'MZ' or struct.unpack_from('<H',data,8)[0]*16!=0x1600:
        raise ValueError('unsupported executable layout')
    expected={0x1fe4:'be60a4c7042b2ec744029021a1b0af894406c7440400009a4410b911',0x1632:'b91e00bb74448b37c6044d83c302e2f6',
              0x2000:'be261dbf36528cc88ed8b890218ec0b93000f3a4'}
    for offset,code in expected.items():
        if data[offset:offset+len(bytes.fromhex(code))]!=bytes.fromhex(code):
            raise ValueError(f'palette/filename evidence differs at {offset:04x}')
    base=0x22f00;variants=[]
    for pointer in struct.unpack_from('<30H',data,base+0x4474):
        end=data.find(b'\0',base+pointer,base+pointer+40)
        if end<0:raise ValueError('unterminated resource filename')
        name=data[base+pointer:end].decode('ascii')
        variants.append(dict(ds_offset=hex(pointer),source=name,variant='M'+name[1:]))
    if not any(row['source']=='SUNRISE.dat' and row['ds_offset']=='0x2e2b' for row in variants):
        raise ValueError('sunrise resource is absent from the rewrite table')
    palette=data[0x3326:0x3356]
    if len(palette)!=48 or max(palette)>63:raise ValueError('invalid six-bit palette')
    return dict(exe_sha256=hashlib.sha256(data).hexdigest(),data_segment_file_base=hex(base),
        palette_file_offset='0x3326',palette_cs_offset='0x1d26',palette_buffer_ds='0x5236',
        palette_rgb6=[list(palette[i:i+3])for i in range(0,48,3)],variants=variants,
        code={hex(o):code for o,code in expected.items()},
        interpretation='SUNRISE.dat becomes MUNRISE.dat through the startup table; the same loader copies the 48-byte CS palette to DS:5236')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();result=inspect(args.exe.read_bytes())
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print('Verified sunrise palette and all 30 resource variant names:',args.out)
