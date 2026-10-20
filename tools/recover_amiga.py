#!/usr/bin/env python3
"""Recover IFF and ProTracker music from the owner's custom Amiga disk.

Every 512-byte physical sector contains 510 payload bytes and a two-byte footer.
Carving physical bytes directly injects footers into files and corrupts decoders.
"""
import argparse
import hashlib
import json
from pathlib import Path
from orig_import import load_ilbm, load_8svx


def payload(disk):
    if len(disk) % 512:
        raise ValueError('Amiga disk must contain complete 512-byte sectors')
    return b''.join(disk[i:i+510] for i in range(0,len(disk),512))


def module_info(data):
    if len(data)<1084 or data[1080:1084]!=b'M.K.':
        raise ValueError('not a 31-sample four-channel MOD')
    orders=data[950]
    if not 1<=orders<=128:raise ValueError('invalid song length')
    patterns=max(data[952:952+orders])+1
    if patterns>128:raise ValueError('invalid pattern order')
    samples=[]
    for i in range(31):
        h=data[20+i*30:50+i*30]
        length=int.from_bytes(h[22:24],'big')*2
        start=int.from_bytes(h[26:28],'big')*2;loop=int.from_bytes(h[28:30],'big')*2
        if h[24]>15 or h[25]>64 or (loop>2 and start+loop>length):
            raise ValueError('invalid instrument metadata')
        samples.append(dict(name=h[:22].rstrip(b'\0').decode('latin1'),bytes=length,
                            finetune=h[24],volume=h[25],loop_start=start,loop_length=loop))
    size=1084+patterns*1024+sum(s['bytes'] for s in samples)
    if size>len(data):raise ValueError('truncated module')
    # A valid pattern cannot select a sample outside the 31-entry header.
    for at in range(1084,1084+patterns*1024,4):
        if ((data[at]&0xf0)|(data[at+2]>>4))>31:
            raise ValueError('invalid pattern instrument')
    return dict(title=data[:20].rstrip(b'\0').decode('latin1'),orders=orders,
                patterns=patterns,size=size,samples=samples)


def recover(adf,out):
    out.mkdir(parents=True,exist_ok=True)
    disk=adf.read_bytes();logical=payload(disk);manifest=dict(source_sha256=hashlib.sha256(disk).hexdigest(),iff=[],modules=[],rejected=[])
    at=0
    while True:
        at=logical.find(b'FORM',at)
        if at<0:break
        kind=logical[at+8:at+12];size=int.from_bytes(logical[at+4:at+8],'big')+8
        if kind in (b'ILBM',b'8SVX') and 12<=size<=len(logical)-at:
            physical=at//510*512+at%510
            file=out/f'{physical:06x}_{kind.decode()}.iff';file.write_bytes(logical[at:at+size])
            try:
                (load_ilbm if kind==b'ILBM' else load_8svx)(file)
                manifest['iff'].append(dict(file=file.name,logical_start=at,physical_start=physical,size=size,kind=kind.decode(),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
            except (ValueError,IndexError) as exc:
                manifest['rejected'].append(dict(physical_start=physical,error=str(exc)));file.unlink()
        at+=4
    at=0
    while True:
        marker=logical.find(b'M.K.',at)
        if marker<0:break
        at=marker+4;start=marker-1080
        if start<0:continue
        try:info=module_info(logical[start:])
        except ValueError:continue
        safe_name=''.join(c for c in info['title'] if c.isalnum() or c in '-_') or f'module_{start:x}'
        file=out/(safe_name+'.mod');file.write_bytes(logical[start:start+info['size']])
        info.update(file=file.name,logical_start=start,physical_start=start//510*512+start%510,sha256=hashlib.sha256(file.read_bytes()).hexdigest())
        manifest['modules'].append(info)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Recovered {len(manifest["iff"])} IFF files and {len(manifest["modules"])} MODs; {len(manifest["rejected"])} invalid IFF rejected')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--adf',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();recover(a.adf,a.out)
