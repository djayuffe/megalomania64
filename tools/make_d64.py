#!/usr/bin/env python3
"""Create one-file formatted standard 35-track Commodore 1541 D64 disk image.
Pure Python. Includes independent image checker that follows the sector chain.
"""
from pathlib import Path
import argparse,math
ROOT=Path(__file__).resolve().parents[1]
SECTORS=lambda t:21 if t<=17 else (19 if t<=24 else (18 if t<=30 else 17))
OFFSET=lambda t,s:256*(sum(SECTORS(i) for i in range(1,t))+s)
SIZE=sum(SECTORS(i) for i in range(1,36))*256

def make_image(prg, dest,filename='MEGALOMANIA'):
 data=Path(prg).read_bytes()
 if len(data)<2 or data[:2]!=b'\x01\x08':raise ValueError('requires BASIC-loadable $0801 PRG')
 if len(filename)>16 or not filename.isascii():raise ValueError('invalid CBM filename')
 disk=bytearray(SIZE);blocks=math.ceil(len(data)/254)
 slots=[]
 for t in range(1,36):
  if t==18:continue
  for s in range(SECTORS(t)):
   slots.append((t,s))
 if blocks>len(slots):raise ValueError('PRG will not fit')
 used=set(slots[:blocks]);used.add((18,0));used.add((18,1))
 for i,(t,s) in enumerate(slots[:blocks]):
  pos=OFFSET(t,s);chunk=data[i*254:(i+1)*254]
  if i+1<blocks:
   nxt=slots[i+1];disk[pos:pos+2]=bytes(nxt)
  else:disk[pos:pos+2]=bytes((0,len(chunk)+1))
  disk[pos+2:pos+2+len(chunk)]=chunk
 bam=OFFSET(18,0)
 disk[bam:bam+4]=bytes((18,1,65,0))
 for t in range(1,36):
  sectors=SECTORS(t);free=[s for s in range(sectors) if (t,s) not in used]
  b=bam+4+(t-1)*4
  disk[b]=len(free)
  for s in free:disk[b+1+s//8] |= 1<<(s%8)
 disk[bam+0x90:bam+0xa0]=b'ISLAND WARS'.ljust(16,b'\xa0')
 disk[bam+0xa2:bam+0xa4]=b'IW'
 disk[bam+0xa4:bam+0xa7]=bytes((0xa0,ord('2'),ord('A')))
 dire=OFFSET(18,1)
 disk[dire:dire+2]=bytes((0,0xff))
 disk[dire+2]=0x82
 disk[dire+3:dire+5]=bytes(slots[0])
 disk[dire+5:dire+21]=filename.upper().encode('ascii').ljust(16,b'\xa0')
 disk[dire+30]=blocks&0xff;disk[dire+31]=blocks>>8
 dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(disk)
 verify_image(dest,data)
 return blocks

def verify_image(image,original=None):
 disk=Path(image).read_bytes()
 if len(disk)!=174848:raise ValueError('not a 35-track D64 image')
 bam=OFFSET(18,0);dire=OFFSET(18,1)
 if disk[bam:bam+2]!=bytes((18,1)):raise ValueError('broken dir pointer')
 if disk[dire+2]!=0x82:raise ValueError('directory lacks closed PRG')
 t,s=disk[dire+3:dire+5];chain=[];reassembled=bytearray()
 while t:
  if t not in range(1,36) or s>=SECTORS(t) or (t,s) in chain:raise ValueError('invalid file chain')
  chain.append((t,s));b=disk[OFFSET(t,s):OFFSET(t,s)+256];next_t,next_s=b[:2]
  count=254 if next_t else next_s-1
  if not 0<=count<=254:raise ValueError('invalid final byte count')
  reassembled.extend(b[2:2+count]);t,s=next_t,next_s
 total=disk[dire+30] + 256*disk[dire+31]
 if total!=len(chain):raise ValueError('file block count mismatch')
 for track in range(1,36):
  ofs=bam+4+(track-1)*4;free=[s for s in range(SECTORS(track)) if disk[ofs+1+s//8]&(1<<(s%8))]
  if len(free)!=disk[ofs]:raise ValueError('BAM free count mismatch')
  if any(disk[ofs+1+s//8]&(1<<(s%8)) for t,s in chain if t==track):raise ValueError('BAM counts allocated sector free')
 if original is not None and reassembled!=original:raise ValueError('sector-chain payload differs from PRG')
 return bytes(reassembled)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',default=str(ROOT/'dist/MegaLoMania64.prg'));p.add_argument('--output',default=str(ROOT/'dist/MegaLoMania64.d64'));args=p.parse_args()
 n=make_image(args.input,args.output)
 print(f'PASS: {args.output} ({SIZE} bytes, {n} PRG blocks)')
