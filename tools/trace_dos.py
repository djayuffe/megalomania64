"""Bounded diagnostic trace of the owner-supplied DOS executable.

Requires optional Unicorn 2.x. This models enough BIOS/DOS calls to trace the
intro and resource opens. It has no cycle-accurate VGA, interrupts, or game input;
its frame counts describe calls to the original retrace routine, not elapsed time.
DOS writes stay in virtual files. Only the report and memory snapshot reach disk.
"""
import argparse,sys,struct,json
from pathlib import Path
from unicorn import *
from unicorn.x86_const import *
REG={name:globals()['UC_X86_REG_'+name.upper()]for name in ['ax','bx','cx','dx','si','di','bp','sp','cs','ds','es','ss','ip','eflags']}
class Machine:
 def __init__(self,folder,out):
  self.folder=Path(folder);self.out=Path(out);self.out.mkdir(parents=True,exist_ok=True)
  self.events=[];self.files={};self.handles={};self.next_handle=5;self.video=3;self.crtc={};self.seq={};self.ports={};self.ticks=0;self.frames=0;self.port_n=0;self.heap=0x45c0;self.stop_reason='instruction bound';self.module_seg=0x1000;self.ds=self.module_seg+0x2190
  data=(self.folder/'MEGA.EXE').read_bytes();hdr=struct.unpack_from('<14H',data);self.data=data;self.uc=Uc(UC_ARCH_X86,UC_MODE_16);u=self.uc;u.mem_map(0,0x200000)
  image=bytearray(data[hdr[4]*16:])
  for i in range(hdr[3]):
   off,seg=struct.unpack_from('<HH',data,hdr[12]+i*4);at=seg*16+off;value=struct.unpack_from('<H',image,at)[0];struct.pack_into('<H',image,at,(value+self.module_seg)&65535)
  u.mem_write(self.module_seg*16,bytes(image));self.psp=self.module_seg-16;u.mem_write(self.psp*16,b'\xcd\x20');u.mem_write(self.psp*16+0x80,b'\0\r');u.mem_write(self.psp*16+0x2c,struct.pack('<H',0x900));u.mem_write(0x9000,b'PATH=C:\\\0\0\1\0C:\\MEGA.EXE\0');u.mem_write(0x413,struct.pack('<H',640))
  for r,v in [('cs',self.module_seg+hdr[11]),('ip',hdr[10]),('ss',self.module_seg+hdr[7]),('sp',hdr[8]),('ds',self.psp),('es',self.psp),('eflags',0x202)]:self.w(r,v)
  u.hook_add(UC_HOOK_INTR,self.interrupt)
  u.hook_add(UC_HOOK_INSN,self.input,None,1,0,UC_X86_INS_IN);u.hook_add(UC_HOOK_INSN,self.output,None,1,0,UC_X86_INS_OUT)
  addr=self.module_seg*16+0x13de8-0x1600;u.hook_add(UC_HOOK_CODE,self.retrace,None,addr,addr)
 def r(self,n):return self.uc.reg_read(REG[n])
 def w(self,n,v):self.uc.reg_write(REG[n],v)
 def flag(self,mask,on):self.w('eflags',(self.r('eflags')|mask)if on else(self.r('eflags')&~mask))
 def text(self,seg,off,term=b'\0'):
  raw=bytes(self.uc.mem_read(seg*16+off,256));return raw.split(term)[0].decode('latin1')
 def event(self,kind,**values):
  v=dict(kind=kind,frame=self.frames,pc=hex(self.r('cs')*16+self.r('ip')-self.module_seg*16+0x1600),**values);self.events.append(v)
  if kind not in ['crtc','out','retrace']:print(v,flush=True)
 def interrupt(self,u,n,_):
  ax=self.r('ax');ah=ax>>8;al=ax&255;bx=self.r('bx');cx=self.r('cx');dx=self.r('dx');ds=self.r('ds');es=self.r('es')
  self.flag(1,False)
  if n==0x21:
   if ah in [0x4a,0x49]:return
   if ah==0x48:
    if self.heap+bx>0x9f00:self.w('bx',0x9f00-self.heap);self.w('ax',8);self.flag(1,True)
    else:self.w('ax',self.heap);self.event('alloc',segment=hex(self.heap),paragraphs=bx);self.heap+=bx
    return
   if ah in [0x07,0x08,0x01]:self.w('ax',13);return
   if ah==0x30:self.w('ax',0x0005);return
   if ah==0x25:u.mem_write(al*4,struct.pack('<HH',dx,ds));return
   if ah==0x35:
    off,seg=struct.unpack('<HH',u.mem_read(al*4,4));self.w('bx',off);self.w('es',seg);return
   if ah in [0x3d,0x3c]:
    name=self.text(ds,dx).replace('\\','/').split('/')[-1].upper();matches=[p for p in self.folder.iterdir()if p.name.upper()==name]
    if not matches and ah==0x3d:self.w('ax',2);self.flag(1,True);self.event('missing',file=name);return
    data=matches[0].read_bytes()if matches and ah==0x3d else b'';h=self.next_handle;self.next_handle+=1;self.handles[h]=[data,0,name];self.w('ax',h);self.event('open',file=name,size=len(data),display_start=struct.unpack('<H',u.mem_read(self.ds*16+0xaf7d,2))[0],stride=struct.unpack('<H',u.mem_read(self.ds*16+0xaf7f,2))[0]);return
   if ah==0x3f:
    if bx not in self.handles:self.w('ax',6);self.flag(1,True);return
    f=self.handles[bx];part=f[0][f[1]:f[1]+cx];u.mem_write(ds*16+dx,part);f[1]+=len(part);self.w('ax',len(part));return
   if ah==0x42:
    f=self.handles[bx];off=(cx<<16)|dx
    if off&0x80000000:off-=1<<32
    f[1]=off+(0 if al==0 else f[1]if al==1 else len(f[0]));self.w('ax',f[1]&65535);self.w('dx',f[1]>>16);return
   if ah==0x3e:self.handles.pop(bx,None);return
   if ah==0x40:
    if bx>=5:
     f=self.handles[bx];payload=bytes(u.mem_read(ds*16+dx,cx));f[0]=f[0][:f[1]]+payload+f[0][f[1]+cx:];f[1]+=cx
    self.w('ax',cx);return
   if ah==0x09:self.event('console',text=self.text(ds,dx,b'$')[:200]);return
   if ah==0x2c:self.w('cx',0x0c00);self.w('dx',0);return
   if ah==0x2a:self.w('cx',1991);self.w('dx',0x0801);self.w('ax',0);return
   if ah==0x19:self.w('ax',2);return
   if ah==0x0e:self.w('ax',3);return
   if ah in [0x0b,0x06]:self.w('ax',0);self.flag(0x40,True);return
   if ah==0x4c:self.stop_reason='DOS exit';self.event('exit',status=al);u.emu_stop();return
   self.event('unsupported_int21',ax=hex(ax));self.stop_reason='unsupported DOS';u.emu_stop();return
  if n==0x10:
   self.event('bios_video',ax=hex(ax),bx=hex(bx),cx=hex(cx),dx=hex(dx))
   if ah==0:self.video=al;return
   if ah==0xf:self.w('ax',(80<<8)|self.video);self.w('bx',0);return
   if ax==0x1a00:self.w('ax',0x1a);self.w('bx',8);return
   if ah==0x12:self.w('bx',3);self.w('cx',0);return
   if ah in [0x01,0x02,0x03,0x05,0x06,0x0e,0x10,0x11,0x1b]:return
   self.stop_reason='unsupported video BIOS';u.emu_stop();return
  if n==0x1a:
   self.ticks+=1;self.w('cx',self.ticks>>16);self.w('dx',self.ticks&65535);self.w('ax',0);return
  if n==0x16:self.w('ax',0);self.flag(0x40,True);return
  if n==0x33:self.w('ax',0);self.w('bx',0);return
  if n in [0x11,0x12]:self.w('ax',0x0021 if n==0x11 else 640);return
  if n==0x20:self.stop_reason='DOS int20 exit';u.emu_stop();return
  self.event('unsupported_interrupt',interrupt=hex(n),ax=hex(ax));self.stop_reason='unsupported interrupt';u.emu_stop()
 def input(self,u,port,size,_):
  if port in [0x3da,0x3ba]:self.port_n+=1;return 8 if self.port_n&1 else 0
  if port in [0x3d5,0x3b5]:return self.crtc.get(self.ports.get(port-1,0),0)
  if port==0x3cc:return 0xe3
  if port==0x201:return 255
  return 0
 def output(self,u,port,size,value,_):
  if size==2:self.output(u,port,1,value&255,None);self.output(u,port+1,1,value>>8,None);return
  self.ports[port]=value
  if port==0x3d5:
   index=self.ports.get(0x3d4,0);self.crtc[index]=value
   if index in [0xc,0xd,0x13,0x18]:self.event('crtc',register=index,value=value,display_start=self.crtc.get(0xc,0)*256+self.crtc.get(0xd,0))
 def retrace(self,u,address,size,_):
  self.frames+=1
  if self.frames%1000==0:print('frame',self.frames,'video',self.video,flush=True)
  if self.frames>=12000:self.stop_reason='frame bound';u.emu_stop()
 def run(self):
  try:self.uc.emu_start(self.r('cs')*16+self.r('ip'),0x1fffff,timeout=25000000,count=100000000)
  except UcError as e:self.stop_reason=str(e);self.event('cpu_error',error=str(e))
  finally:
   self.event('stop',reason=self.stop_reason,cs=hex(self.r('cs')),ip=hex(self.r('ip')))
   (self.out/'trace.json').write_text(json.dumps(self.events,indent=2)+'\n');(self.out/'memory.bin').write_bytes(self.uc.mem_read(0,0x100000))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--dos',required=True,type=Path)
 parser.add_argument('--out',required=True,type=Path)
 args=parser.parse_args()
 root=Path(__file__).resolve().parents[1]
 if args.out.resolve().is_relative_to(root):parser.error('keep executable-derived traces outside the source checkout')
 from intro_timeline import inspect
 inspect((args.dos/'MEGA.EXE').read_bytes())
 Machine(args.dos,args.out).run()
