"""Small, instruction-accurate-enough legal 6502 runner for game boot/logic smoke tests.
Not a cycle-accurate emulator and not a substitute for VICE/HW testing.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from asm6502 import OPC

DECODER={int(op):(name,mode) for name,modes in OPC.items() for mode,op in modes.items()}
C=1;Z=2;I=4;D=8;B=16;U=32;V=64;N=128

class CPU:
 def __init__(self,prg):
  buf=Path(prg).read_bytes();start=buf[0]+256*buf[1]
  self.m=bytearray(65536);self.m[start:start+len(buf)-2]=buf[2:];self.m[0xdc00]=255
  self.a=self.x=self.y=0;self.s=0xfd;self.p=0x24;self.pc=0x1000;self.steps=0;self.key=0;self.drive_files={};self.channels={};self.input_channel=None;self.filename="";self.lfs=(1,8,1)
  self.in_irq=False;self.joystick=0xff;self.raster_msb=0;self.io_screen=[];self.status=0;self.drive_device=8;self.write_protected=False;self.disk_log=[]
 def flag(self,f):return bool(self.p&f)
 def set(self,f,v):self.p=(self.p|f) if v else (self.p & (~f&255))
 def nz(self,v):self.set(Z,(v&255)==0);self.set(N,bool(v&128));return v&255
 def fetch(self):v=self.m[self.pc];self.pc=(self.pc+1)&65535;return v
 def fetch16(self):return self.fetch() |(self.fetch()<<8)
 def push(self,v):self.m[0x100+self.s]=v&255;self.s=(self.s-1)&255
 def pop(self):self.s=(self.s+1)&255;return self.m[0x100+self.s]
 def adc(self,v):
  x=self.a+v+(1 if self.flag(C) else 0);r=x&255
  self.set(C,x>255);self.set(V, bool((~(self.a^v)&(self.a^r)&0x80)))
  self.a=self.nz(r)
 def sbc(self,v):self.adc(v^255)
 def compare(self,l,r):
  z=(l-r)&255;self.set(C,l>=r);self.nz(z)
 def step(self):
  pc=self.pc;op=self.fetch()
  if op not in DECODER:raise AssertionError(f'invalid opcode ${op:02X} at ${pc:04X}')
  name,mode=DECODER[op];self.steps+=1
  if name=='RTI':   # NMI handlers end here (the sample player); IRQs leave through the $EA31/$EA81 shim
   self.p=self.pop()|U;self.pc=self.pop()|(self.pop()<<8);return
  if name=='BRK':raise AssertionError(f'unsupported interrupt ${pc:04X}')
  if name=='JSR':
   addr=self.fetch16()
   if addr==0xffe4 and self.input_channel is None:
    self.a=self.nz(self.key);self.key=0;return
   if addr==0xffba:  # SETLFS - unit-test KERNAL disk shim
    self.lfs=(self.a,self.x,self.y);return
   if addr==0xffbd:  # SETNAM
    self.filename=bytes(self.m[(self.x|(self.y<<8)):(self.x|(self.y<<8))+self.a]).decode('ascii');return
   if addr in (0xffc0,0xffd8,0xffd5):self.io_screen.append((self.m[0xd011]&0x10,self.m[0xd015],self.m[0xd011]&0x80))
   if addr==0xffc6:  # CHKIN
    self.input_channel=self.x
    self.set(C,self.x not in self.channels);return
   if addr in (0xffcf,0xffe4):  # CHRIN / GETIN from a selected input channel, including valid last byte with EOF status
    channel=self.channels.get(self.input_channel)
    if channel is None:
     self.status=0x80;self.a=self.nz(0);return
    image,pos=channel
    if pos>=len(image):
     self.status=0x40;self.a=self.nz(0);return
    self.a=self.nz(image[pos]);channel[1]+=1
    self.status=0x40 if channel[1]==len(image) else 0;return
   if addr==0xffc3:
    self.channels.pop(self.a,None);return
   if addr==0xffcc:
    self.input_channel=None;return
   if addr==0xffc0:  # OPEN: DOS command channel and sequential data channels
    if self.lfs[0]==15 and self.lfs[2]==15 and self.lfs[1]==self.drive_device:
     name=self.filename
     self.disk_log.append(('cmd',name))
     if name.startswith('S0:') and not self.write_protected:self.drive_files.pop(name[3:],None)
     self.set(C,False)
    elif self.lfs[1]==self.drive_device and self.filename in self.drive_files:
     self.channels[self.lfs[0]]=[self.drive_files[self.filename],0]
     self.disk_log.append(('open',self.filename));self.status=0;self.set(C,False)
    else:
     self.status=0x42;self.set(C,True)
    return
   if addr==0xffb7:  # READST
    self.a=self.nz(self.status);return
   if addr==0xffd8:  # SAVE: A=ZP pointer, X/Y=end exclusive
    zp=self.a;start=self.m[zp] | (self.m[(zp+1)&255]<<8);end=self.x|(self.y<<8)
    self.status=0
    if end<=start or self.lfs[1]!=self.drive_device or self.filename.startswith('@'):
     self.set(C,True);return
    self.disk_log.append(('save',self.filename))
    # A write-protected disk reports its error on the DOS error channel only; SAVE itself looks fine.
    if not self.write_protected:
     if self.filename in self.drive_files:  # real DOS refuses to overwrite without scratch/@
      self.set(C,False);return
     self.drive_files[self.filename]=bytes([start&255,start>>8])+bytes(self.m[start:end])
    self.set(C,False);return
   if addr==0xffd5:  # LOAD (A=0) / VERIFY (A=1)
    verify=self.a==1
    image=self.drive_files.get(self.filename)
    if image is None or len(image)<2 or self.lfs[1]!=self.drive_device:
     self.status=0x80 if self.lfs[1]!=self.drive_device else 0x42
     self.set(C,True);return
    start=(image[0]|image[1]<<8) if self.lfs[2] else (self.x|(self.y<<8))
    end=start+len(image)-2
    if end>65536:
     self.set(C,True);return
    if verify:
     self.status=0x40 if bytes(self.m[start:end])==image[2:] else 0x50
     self.set(C,False);return
    self.m[start:end]=image[2:];self.x=end&255;self.y=end>>8;self.status=0x40;self.set(C,False);return
   ret=(self.pc-1)&65535;self.push(ret>>8);self.push(ret&255);self.pc=addr;return
  if name=='RTS':self.pc=((self.pop() |(self.pop()<<8))+1)&65535;return
  if name=='JMP':
   a=self.fetch16()
   if mode=='abs' and a in (0xea31,0xea81):
    if self.in_irq:  # KERNAL IRQ tail: pull Y,X,A then RTI
     self.y=self.pop();self.x=self.pop();self.a=self.pop();self.p=self.pop()|U
     self.pc=self.pop()|(self.pop()<<8);self.in_irq=False
    else:self.pc=0xfff0   # direct call of a handler from a test
    return
   self.pc=a if mode=='abs' else (self.m[a] | (self.m[(a&0xff00)|((a+1)&255)]<<8))
   return
  if mode=='rel':
   off=self.fetch();diff=off if off<128 else off-256
   test={'BCC':not self.flag(C),'BCS':self.flag(C),'BEQ':self.flag(Z),'BNE':not self.flag(Z),'BMI':self.flag(N),'BPL':not self.flag(N),'BVC':not self.flag(V),'BVS':self.flag(V)}[name]
   if test:self.pc=(self.pc+diff)&65535
   return
  if mode=='imp' or mode=='acc':
   if name=='CLC':self.set(C,False)
   elif name=='SEC':self.set(C,True)
   elif name=='SEI':self.set(I,True)
   elif name=='CLI':self.set(I,False)
   elif name=='CLD':self.set(D,False)
   elif name=='SED':self.set(D,True)
   elif name=='TAX':self.x=self.nz(self.a)
   elif name=='TAY':self.y=self.nz(self.a)
   elif name=='TXA':self.a=self.nz(self.x)
   elif name=='TYA':self.a=self.nz(self.y)
   elif name=='INX':self.x=self.nz(self.x+1)
   elif name=='INY':self.y=self.nz(self.y+1)
   elif name=='DEX':self.x=self.nz(self.x-1)
   elif name=='DEY':self.y=self.nz(self.y-1)
   elif name=='PHP':self.push(self.p|B|U)
   elif name=='PLP':self.p=(self.pop()&~B)|U
   elif name=='PHA':self.push(self.a)
   elif name=='PLA':self.a=self.nz(self.pop())
   elif name=='NOP':pass
   elif name in ('ASL','LSR','ROL','ROR'):
    v=self.a;carry=self.flag(C)
    if name=='ASL':self.set(C,bool(v&128));v=(v<<1)&255
    elif name=='LSR':self.set(C,bool(v&1));v>>=1
    elif name=='ROL':self.set(C,bool(v&128));v=((v<<1)|(1 if carry else 0))&255
    else:self.set(C,bool(v&1));v=(v>>1)|(128 if carry else 0)
    self.a=self.nz(v)
   else:raise AssertionError(f'unimplemented implied {name} at ${pc:04X}')
   return
  addr=None
  if mode=='imm':v=self.fetch()
  else:
   if mode=='zp':addr=self.fetch()
   elif mode=='zpx':addr=(self.fetch()+self.x)&255
   elif mode=='zpy':addr=(self.fetch()+self.y)&255
   elif mode=='abs':addr=self.fetch16()
   elif mode=='absx':addr=(self.fetch16()+self.x)&65535
   elif mode=='absy':addr=(self.fetch16()+self.y)&65535
   elif mode in ('indx','indy'):
    zp=self.fetch()
    if mode=='indx':zp=(zp+self.x)&255
    lo=self.m[zp];hi=self.m[(zp+1)&255];addr=lo+(hi<<8)
    if mode=='indy':addr=(addr+self.y)&65535
   else:raise AssertionError(f'unsupported mode {mode} at ${pc:04X}')
   v=self.m[addr]
   if addr==0xdc00 and name in ('LDA','LDX','LDY'):v=self.joystick   # port 2 pins, not the written output latch
   if addr==0xd011 and name in ('LDA','LDX','LDY'):v=(v&0x7f)|(self.raster_msb<<7)   # bit 7 reads the live raster MSB
  if name=='LDA':self.a=self.nz(v)
  elif name=='LDX':self.x=self.nz(v)
  elif name=='LDY':self.y=self.nz(v)
  elif name=='STA':self.m[addr]=self.a
  elif name=='STX':self.m[addr]=self.x
  elif name=='STY':self.m[addr]=self.y
  elif name=='ADC':self.adc(v)
  elif name=='SBC':self.sbc(v)
  elif name=='CMP':self.compare(self.a,v)
  elif name=='CPX':self.compare(self.x,v)
  elif name=='CPY':self.compare(self.y,v)
  elif name=='AND':self.a=self.nz(self.a&v)
  elif name=='ORA':self.a=self.nz(self.a|v)
  elif name=='EOR':self.a=self.nz(self.a^v)
  elif name=='INC':self.m[addr]=self.nz(v+1)
  elif name=='DEC':self.m[addr]=self.nz(v-1)
  elif name in ('ASL','LSR','ROL','ROR'):
   carry=self.flag(C)
   if name=='ASL':self.set(C,bool(v&128));v=(v<<1)&255
   elif name=='LSR':self.set(C,bool(v&1));v>>=1
   elif name=='ROL':self.set(C,bool(v&128));v=((v<<1)|(1 if carry else 0))&255
   else:self.set(C,bool(v&1));v=(v>>1)|(128 if carry else 0)
   self.m[addr]=self.nz(v)
  elif name=='BIT':self.set(Z,(v&self.a)==0);self.set(N,v&128);self.set(V,v&64)
  else:raise AssertionError(f'unimplemented {name} at ${pc:04X}')
 def call(self,addr,max_ops=400000):
  # emulate external JSR from a safe dummy $8000 entry
  self.push(0xff);self.push(0xef);self.pc=addr
  count=0;s0=self.s+2
  while self.pc!=0xfff0:
   self.step();count+=1
   if count>max_ops:raise AssertionError(f'runaway at ${self.pc:04X}: {count} instructions')
  self.s=s0&255
  return count
 def fire_irq(self):
  """Emulate the 6510 + KERNAL IRQ entry ($FF48) for a raster interrupt."""
  if self.p&I or self.in_irq:return False
  self.push(self.pc>>8);self.push(self.pc&255);self.push(self.p&~B&255)
  self.set(I,True)
  self.push(self.a);self.push(self.x);self.push(self.y)
  self.m[0xd019]=0x81
  self.pc=self.m[0x314]|(self.m[0x315]<<8);self.in_irq=True
  return True
 def run_irq(self,max_ops=200000):
  """Fire one raster IRQ and run it to its RTI. Returns the instruction count."""
  pc,a,x,y,p=self.pc,self.a,self.x,self.y,self.p
  if not self.fire_irq():raise AssertionError('interrupts masked')
  n=0
  while self.in_irq:
   self.step();n+=1
   if n>max_ops:raise AssertionError('IRQ runaway')
  assert (self.pc,self.a,self.x,self.y)==(pc,a,x,y),'IRQ did not restore registers'
  return n
 def run_until(self,target,max_steps=3000000,irq_every=2500,on_pc=None):
  """Free-run like a machine: raster IRQ every `irq_every` instructions while interrupts are on."""
  n=0;since=0
  while self.pc!=target:
   if on_pc:on_pc(self)
   self.step();n+=1;since+=1
   if not self.in_irq and since>=irq_every and not self.p&I:
    self.fire_irq();since=0
   if n>max_steps:raise AssertionError(f'did not reach ${target:04X}; pc=${self.pc:04X}')
  return n
 def run_for(self,steps,irq_every=5700,on_pc=None):
  """Free-run for a number of instructions with periodic raster IRQs (~1 frame = 5700 instr.)."""
  since=0
  for _ in range(steps):
   if on_pc:on_pc(self)
   self.step();since+=1
   if not self.in_irq and since>=irq_every and not self.p&I:
    self.fire_irq();since=0
