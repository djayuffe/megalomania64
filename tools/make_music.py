#!/usr/bin/env python3
"""Adapt recovered four-channel MOD note timing to three SID voices.

Preserves note onsets, speed changes, pattern breaks, and fade-to-silence times.
Channel 0 is omitted; sample timbres and continuous volume slides are approximated
by SID waveforms and note gates. This is a score adaptation, not Paula emulation.
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
from recover_amiga import module_info

# PCM instrument -> SID oscillator; the choice of waveform is a port arrangement.
WAVES = {1:3, 2:3, 3:2, 4:2, 5:1, 6:2, 7:0, 8:0, 10:1, 11:2, 12:1, 13:1}


def score(data):
    info=module_info(data);order=list(data[952:952+info['orders']])
    samples=info['samples'];instrument=[0]*4;volume=[0]*4;active=[False]*4
    speed,tempo=6,125;clock=Fraction(0);events={};position,row=0,0;seen=set()
    while position<len(order):
        if (position,row) in seen:raise ValueError('unsupported looping pattern control')
        seen.add((position,row));commands=[];notes=[0]*3;next_row=None
        for channel in range(4):
            at=1084+order[position]*1024+row*16+channel*4
            a,b,c,d=data[at:at+4];period=((a&15)<<8)|b;sample=(a&0xf0)|(c>>4);fx=c&15
            if sample:instrument[channel]=sample;volume[channel]=samples[sample-1]['volume']
            if fx==0xc:volume[channel]=min(64,d)
            if fx==0xf:
                if d==0:raise ValueError('unsupported stop command')
                if d<32:speed=d
                else:tempo=d
            if fx==0xd:
                next_row=(d>>4)*10+(d&15)
                if next_row>=64:raise ValueError('invalid pattern break')
            if fx not in (0,0xa,0xc,0xd,0xf) or (fx==0 and d):
                raise ValueError(f'unsupported MOD effect {fx:x}{d:02x}')
            commands.append((fx,d))
            if channel and period:
                midi=36+round(12*math.log2(856/period))
                note=midi-24+1
                if not 1<=note<=63:raise ValueError('SID note index outside bank')
                notes[channel-1]=(WAVES.get(instrument[channel],2)<<6)|note
                active[channel]=True
        for tick in range(speed):
            changed=notes[:] if tick==0 else [0]*3
            for channel,(fx,param) in enumerate(commands):
                if tick and fx==0xa:
                    volume[channel]=max(0,min(64,volume[channel]+(param>>4)-(param&15)))
                if channel and active[channel] and volume[channel]==0:
                    changed[channel-1]=255;active[channel]=False
            if any(changed):
                target=events.setdefault(round(clock),[0]*3)
                for i,value in enumerate(changed):
                    if value:target[i]=value
            clock+=Fraction(125,tempo)
        if next_row is not None:position+=1;row=next_row
        else:
            row+=1
            if row==64:position+=1;row=0
    end=max(round(clock),max(events,default=0)+1);events[end]=[255]*3
    if 0 not in events:events[0]=[255]*3
    ordered=sorted(events.items());stream=bytearray()
    for i,(at,notes) in enumerate(ordered):
        duration=ordered[i+1][0]-at if i+1<len(ordered) else 1
        while duration>255:
            stream.extend([255,*notes]);notes=[0]*3;duration-=255
        stream.extend([duration,*notes])
    stream.extend(bytes(4))
    return bytes(stream),dict(title=info['title'],events=len(ordered),frames=end,seconds=end/50,
                              omitted_channel=0,limitations=['Paula sample timbres','continuous volume fades','sample finetune'])


def build(amiga,out):
    out.mkdir(parents=True,exist_ok=True)
    scores=[];metadata=[]
    for name in ['choose3','war14']:
        stream,info=score((amiga/(name+'.mod')).read_bytes());scores.append(stream);metadata.append(info)
    # Bank layout: PAL/NTSC note tables, then two absolute stream pointers.
    bank=bytearray()
    for clock in [985248,1022727]:
        for note in range(64):
            frequency=0 if note==0 else 440*2**(((note-1+24)-69)/12)
            bank.extend(round(frequency*2**24/clock).to_bytes(2,'little'))
    cursor=0xc504
    for stream in scores:bank.extend(cursor.to_bytes(2,'little'));cursor+=len(stream)
    for stream in scores:bank.extend(stream)
    if len(bank)>0xc00:raise ValueError(f'SID score bank too large: {len(bank)} > 3072')
    file=b'MLM1'+len(bank).to_bytes(2,'little')+bank
    (out/'MUSIC.bin').write_bytes(file)
    (out/'music.json').write_text(json.dumps(dict(bytes=len(bank),tunes=metadata),indent=2)+'\n')
    print(f'SID scores: {len(bank)} resident bytes',metadata)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--amiga',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();build(a.amiga,a.out)
