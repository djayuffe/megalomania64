#!/usr/bin/env python3
"""Arrange all four recovered MOD channels for SID, retaining quantized dynamics.

Channels 0/1 share SID voice 1 as a 50 Hz alternating arpeggio; channels 2/3
have dedicated oscillators. This remains a SID arrangement, not Paula emulation.
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
from recover_amiga import module_info

WAVES = {1:3,2:3,3:2,4:2,5:1,6:2,7:0,8:0,10:1,11:2,12:3,13:3}


def score(data):
    info=module_info(data);order=list(data[952:952+info['orders']])
    samples=info['samples'];instrument=[0]*4;volume=[0]*4;active=[False]*4;previous=[None]*4
    speed,tempo=6,125;clock=Fraction(0);events={};position,row=0,0;seen=set()
    while position<len(order):
        if (position,row,speed,tempo) in seen:raise ValueError('unsupported looping pattern control')
        seen.add((position,row,speed,tempo));commands=[];notes=[0]*4;next_row=None
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
            if period:
                fine=samples[instrument[channel]-1]['finetune'] if instrument[channel] else 0
                fine=fine if fine<8 else fine-16
                midi=36+round(12*math.log2(856/period)+fine/8)
                note=midi-24+1
                if not 1<=note<=62:raise ValueError('SID note index outside bank')
                notes[channel]=(WAVES.get(instrument[channel],2)<<6)|note
                active[channel]=True
        for tick in range(speed):
            changed={}
            for channel,(fx,param) in enumerate(commands):
                if tick and fx==0xa:
                    # ProTracker gives the upper nibble priority, not up minus down.
                    delta=(param>>4) if param>>4 else -(param&15)
                    volume[channel]=max(0,min(64,volume[channel]+delta))
                amp=round(volume[channel]*15/64) if active[channel] else 0
                note=notes[channel] if tick==0 else 0
                if note or amp!=previous[channel]:changed[channel]=(note,amp);previous[channel]=amp
            if changed:events.setdefault(round(clock),{}).update(changed)
            clock+=Fraction(125,tempo)
        if next_row is not None:position+=1;row=next_row
        else:
            row+=1
            if row==64:position+=1;row=0
    end=max(round(clock),max(events,default=0)+1);events[end]={c:(255,0)for c in range(4)}
    if 0 not in events:events[0]={c:(255,0)for c in range(4)}
    ordered=sorted(events.items());stream=bytearray()
    for i,(at,changes) in enumerate(ordered):
        duration=ordered[i+1][0]-at if i+1<len(ordered) else 1
        while duration>255:
            emit(stream,255,changes);changes={};duration-=255
        emit(stream,duration,changes)
    stream.append(0)
    return bytes(stream),dict(title=info['title'],events=len(ordered),frames=end,seconds=end/50,
        channels=4,shared_sid_voice=[0,1],limitations=['SID timbres replace samples','4-bit sustain dynamics','finetune rounded to semitones'])


def emit(stream,duration,changes):
    stream.extend((duration,sum(1<<c for c in changes)))
    for channel in range(4):
        if channel in changes:stream.extend(changes[channel])


def build(amiga,out):
    out.mkdir(parents=True,exist_ok=True);metadata=[]
    for name,file in [('choose3','MUSIC'),('war14','MUSICG')]:
        stream,info=score((amiga/(name+'.mod')).read_bytes());bank=bytearray()
        for clock in [985248,1022727]:
            for note in range(64):
                frequency=0 if note==0 else 440*2**(((note-1+24)-69)/12)
                bank.extend(round(frequency*2**24/clock).to_bytes(2,'little'))
        bank.extend(stream)
        if len(bank)>0x1000:raise ValueError(f'SID score bank too large: {len(bank)} > 4096')
        (out/(file+'.bin')).write_bytes(b'MLM2'+len(bank).to_bytes(2,'little')+bank)
        metadata.append(dict(file=file,bytes=len(bank),**info))
    (out/'music.json').write_text(json.dumps(dict(tunes=metadata),indent=2)+'\n')
    print('Four-channel SID arrangements:',metadata)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--amiga',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();build(a.amiga,a.out)
