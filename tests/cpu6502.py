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
  self.a=self.x=self.y=0;self.s=0xfd;self.p=0x24;self.pc=0x1000;self.steps=0;self.key=0;self.drive_files={};self.filename="";self.lfs=(1,8,1)
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
  if name in ('BRK','RTI'):raise AssertionError(f'unsupported interrupt ${pc:04X}')
  if name=='JSR':
   addr=self.fetch16()
   if addr==0xffe4:
    self.a=self.nz(self.key);self.key=0;return
   if addr==0xffba:  # SETLFS - unit-test KERNAL disk shim
    self.lfs=(self.a,self.x,self.y);return
   if addr==0xffbd:  # SETNAM
    self.filename=bytes(self.m[(self.x|(self.y<<8)):(self.x|(self.y<<8))+self.a]).decode('ascii');return
   if addr==0xffd8:  # SAVE: A=ZP pointer, X/Y=end exclusive
    zp=self.a;start=self.m[zp] | (self.m[(zp+1)&255]<<8);end=self.x|(self.y<<8)
    if end<=start or self.lfs[1]!=8:
     self.set(C,True);return
    name=self.filename.removeprefix('@0:')
    self.drive_files[name]=bytes([start&255,start>>8])+bytes(self.m[start:end]);self.set(C,False);return
   if addr==0xffd5:  # LOAD: file header address, end address in X/Y
    image=self.drive_files.get(self.filename)
    if image is None or len(image)<2 or self.lfs[1]!=8:
     self.set(C,True);return
    start=(image[0]|image[1]<<8) if self.lfs[2] else (self.x|(self.y<<8))
    end=start+len(image)-2
    if end>65536:
     self.set(C,True);return
    self.m[start:end]=image[2:];self.x=end&255;self.y=end>>8;self.set(C,False);return
   ret=(self.pc-1)&65535;self.push(ret>>8);self.push(ret&255);self.pc=addr;return
  if name=='RTS':self.pc=((self.pop() |(self.pop()<<8))+1)&65535;return
  if name=='JMP':
   a=self.fetch16()
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
  self.push(0x7f);self.push(0xff);self.pc=addr
  count=0
  while self.pc!=0x8000:
   self.step();count+=1
   if count>max_ops:raise AssertionError(f'runaway at ${self.pc:04X}: {count} instructions')
  return count
