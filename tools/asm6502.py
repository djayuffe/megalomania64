#!/usr/bin/env python3
"""Small strict two-pass 6502 assembler for self-contained C64 game builds.
Supports: labels, assignments, *=, !byte, !word, !text, !fill, !bin, 6502 indexed and indirect modes.
Errors on invalid opcodes, overlapping writes, short branches, undefined labels.
"""
import argparse, ast, operator, re, sys
from pathlib import Path

# Mnemonic / addressing-mode opcode matrix for NMOS 6502 (only legal instructions).
OPS = '''
ADC imm:69 zp:65 zpx:75 abs:6D absx:7D absy:79 indx:61 indy:71
AND imm:29 zp:25 zpx:35 abs:2D absx:3D absy:39 indx:21 indy:31
ASL acc:0A zp:06 zpx:16 abs:0E absx:1E
BCC rel:90
BCS rel:B0
BEQ rel:F0
BIT zp:24 abs:2C
BMI rel:30
BNE rel:D0
BPL rel:10
BRK imp:00
BVC rel:50
BVS rel:70
CLC imp:18
CLD imp:D8
CLI imp:58
CLV imp:B8
CMP imm:C9 zp:C5 zpx:D5 abs:CD absx:DD absy:D9 indx:C1 indy:D1
CPX imm:E0 zp:E4 abs:EC
CPY imm:C0 zp:C4 abs:CC
DEC zp:C6 zpx:D6 abs:CE absx:DE
DEX imp:CA
DEY imp:88
EOR imm:49 zp:45 zpx:55 abs:4D absx:5D absy:59 indx:41 indy:51
INC zp:E6 zpx:F6 abs:EE absx:FE
INX imp:E8
INY imp:C8
JMP abs:4C ind:6C
JSR abs:20
LDA imm:A9 zp:A5 zpx:B5 abs:AD absx:BD absy:B9 indx:A1 indy:B1
LDX imm:A2 zp:A6 zpy:B6 abs:AE absy:BE
LDY imm:A0 zp:A4 zpx:B4 abs:AC absx:BC
LSR acc:4A zp:46 zpx:56 abs:4E absx:5E
NOP imp:EA
ORA imm:09 zp:05 zpx:15 abs:0D absx:1D absy:19 indx:01 indy:11
PHA imp:48
PHP imp:08
PLA imp:68
PLP imp:28
ROL acc:2A zp:26 zpx:36 abs:2E absx:3E
ROR acc:6A zp:66 zpx:76 abs:6E absx:7E
RTI imp:40
RTS imp:60
SBC imm:E9 zp:E5 zpx:F5 abs:ED absx:FD absy:F9 indx:E1 indy:F1
SEC imp:38
SED imp:F8
SEI imp:78
STA zp:85 zpx:95 abs:8D absx:9D absy:99 indx:81 indy:91
STX zp:86 zpy:96 abs:8E
STY zp:84 zpx:94 abs:8C
TAX imp:AA
TAY imp:A8
TSX imp:BA
TXA imp:8A
TXS imp:9A
TYA imp:98
'''
OPC={}
for l in OPS.strip().splitlines():
 t=l.split();OPC[t[0]]={k:int(v,16) for k,v in (e.split(':') for e in t[1:])}
BRANCH={k for k,v in OPC.items() if 'rel' in v}

class Unresolved(Exception):pass

def _eval(expr,sym,unknown=False):
 expr=expr.strip()
 if not expr:raise ValueError('empty expression')
 expr=re.sub(r'\$([0-9a-fA-F]+)',r'0x\1',expr)
 expr=re.sub(r'%([01]+)',r'0b\1',expr)
 if expr.startswith('<'):return _eval(expr[1:],sym,unknown)&255
 if expr.startswith('>'):return (_eval(expr[1:],sym,unknown)>>8)&255
 def walk(n):
  if isinstance(n,ast.Constant) and isinstance(n.value,int):return n.value
  if isinstance(n,ast.Constant) and isinstance(n.value,str) and len(n.value)==1:return ord(n.value)
  if isinstance(n,ast.Name):
   if n.id not in sym:
    if unknown:raise Unresolved(n.id)
    raise ValueError('undefined symbol '+n.id)
   return sym[n.id]
  if isinstance(n,ast.UnaryOp) and type(n.op) in (ast.UAdd,ast.USub,ast.Invert):return {ast.UAdd:operator.pos,ast.USub:operator.neg,ast.Invert:operator.invert}[type(n.op)](walk(n.operand))
  if isinstance(n,ast.BinOp) and type(n.op) in (ast.Add,ast.Sub,ast.Mult,ast.FloorDiv,ast.BitAnd,ast.BitOr,ast.LShift,ast.RShift):return {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.FloorDiv:operator.floordiv,ast.BitAnd:operator.and_,ast.BitOr:operator.or_,ast.LShift:operator.lshift,ast.RShift:operator.rshift}[type(n.op)](walk(n.left),walk(n.right))
  raise ValueError('invalid expression '+expr)
 return walk(ast.parse(expr,mode='eval').body)

def split_args(s):
 # commas inside quotes need not split
 out=[]; buf=''; quoted=False; esc=False
 for ch in s:
  if ch=='"' and not esc:quoted=not quoted
  if ch==',' and not quoted:out.append(buf.strip());buf=''
  else:buf+=ch
  esc=(ch=='\\' and not esc)
 if buf.strip():out.append(buf.strip())
 return out

def cut_comment(s):
 quoted=False
 for i,ch in enumerate(s):
  if ch=='"':quoted=not quoted
  if ch==';' and not quoted:return s[:i]
 return s

class Assembler:
 def __init__(self,path):
  self.path=Path(path).resolve();self.sym={};self.mem={};self.labels={};self.entries=[]
  self.lines=self.expand(self.path, [])
 def expand(self,p,stack):
  if p in stack:raise ValueError('cyclic include '+str(p))
  out=[]
  for i,l in enumerate(p.read_text().splitlines(),1):
   l=cut_comment(l).strip()
   if not l:continue
   inc=re.fullmatch(r'!source\s+"([^"]+)"',l)
   if inc:out.extend(self.expand((p.parent/inc[1]).resolve(),stack+[p]))
   else:out.append((str(p),i,l))
  return out
 def eval(self,expr,passno):return _eval(expr,self.sym,unknown=passno==1)
 def emit(self,v,n,pc,passno):
  if passno==2:
   if v is None:raise ValueError('unresolved')
   if v<0 or v>=1<<(8*n):raise ValueError(f'value out of range {v} for {n} bytes')
   for k in range(n):
    addr=pc+k
    if addr>65535:raise ValueError('address overflow')
    if addr in self.mem:raise ValueError(f'overlap at ${addr:04X}')
    self.mem[addr]=(v>>(8*k))&255
  return pc+n
 def run(self,pno):
  pc=None
  for path,lno,raw in self.lines:
   try:
    line=raw
    while True:
     m=re.match(r'^([a-zA-Z_][\w]*):\s*(.*)$',line)
     if not m:break
     k,line=m.groups()
     if pno==1:
      if k in self.sym:raise ValueError('duplicate symbol '+k)
      self.sym[k]=pc
     elif self.sym[k]!=pc:raise ValueError('label shifted '+k)
    if not line:continue
    m=re.fullmatch(r'([A-Za-z_]\w*)\s*=\s*(.+)',line)
    if m:
     name,exp=m.groups()
     if pno==1:
      if name in self.sym:raise ValueError('redefinition '+name)
      self.sym[name]=self.eval(exp,pno)
     continue
    m=re.fullmatch(r'\*\s*=\s*(.+)',line)
    if m:
     pc=self.eval(m[1],pno)
     if not 0<=pc<=65535:raise ValueError('bad origin')
     continue
    if pc is None:raise ValueError('instruction before origin')
    m=re.match(r'^(!\w+)\b\s*(.*)$',line)
    if m:
     directive,args=m.groups()
     if directive=='!byte' or directive=='!word':
      for exp in split_args(args):
       try:v=self.eval(exp,pno)
       except Unresolved:v=0
       pc=self.emit(v,1 if directive=='!byte' else 2,pc,pno)
     elif directive=='!text':
      for arg in split_args(args):
       if arg.startswith('"'):
        b=ast.literal_eval(arg).encode('ascii')
        for v in b:pc=self.emit(v,1,pc,pno)
       else:
        try:v=self.eval(arg,pno)
        except Unresolved:v=0
        pc=self.emit(v,1,pc,pno)
     elif directive=='!fill':
      parts=split_args(args);size=self.eval(parts[0],pno);v=self.eval(parts[1],pno) if len(parts)>1 else 0
      if not 0<=size<65536:raise ValueError('invalid fill')
      for _ in range(size):pc=self.emit(v,1,pc,pno)
     elif directive=='!bin':
      f=ast.literal_eval(args)
      for v in (Path(path).parent/f).read_bytes():pc=self.emit(v,1,pc,pno)
     else:raise ValueError('unknown directive '+directive)
     continue
    a=line.split(None,1);mn=a[0].upper();arg=a[1].strip() if len(a)>1 else ''
    if mn.startswith('LB') and mn[1:] in BRANCH:
     inverse={'BEQ':'BNE','BNE':'BEQ','BCC':'BCS','BCS':'BCC','BMI':'BPL','BPL':'BMI','BVC':'BVS','BVS':'BVC'}[mn[1:]]
     pc=self.emit(OPC[inverse]['rel'],1,pc,pno)
     pc=self.emit(3,1,pc,pno)
     pc=self.emit(OPC['JMP']['abs'],1,pc,pno)
     try:dest=self.eval(arg,pno)
     except Unresolved:dest=0
     pc=self.emit(dest,2,pc,pno)
     continue
    if mn not in OPC:raise ValueError('unknown mnemonic '+mn)
    if not arg:mode='acc' if mn in ('ASL','LSR','ROL','ROR') else 'imp';exp=None
    elif arg.upper()=='A':mode='acc';exp=None
    elif mn in BRANCH:mode='rel';exp=arg
    elif arg.startswith('#'):mode='imm';exp=arg[1:]
    elif arg.startswith('('):
     m=re.fullmatch(r'\(([^()]+),\s*[xX]\)',arg)
     if m:mode='indx';exp=m[1]
     else:
      m=re.fullmatch(r'\(([^()]+)\),\s*[yY]',arg)
      if m:mode='indy';exp=m[1]
      else:
       m=re.fullmatch(r'\(([^()]+)\)',arg)
       if not m:raise ValueError('invalid indirect syntax')
       mode='ind';exp=m[1]
    else:
     m=re.fullmatch(r'(.+),\s*([xXyY])',arg)
     exp=m[1] if m else arg
     reg=m[2].lower() if m else ''
     try:value=self.eval(exp,pno)
     except Unresolved:value=65535
     if reg=='x':mode='zpx' if value<256 and 'zpx' in OPC[mn] else 'absx'
     elif reg=='y':mode='zpy' if value<256 and 'zpy' in OPC[mn] else 'absy'
     else:mode='zp' if value<256 and 'zp' in OPC[mn] else 'abs'
    if mode not in OPC[mn]:raise ValueError(f'{mn} has no {mode} addressing')
    pc=self.emit(OPC[mn][mode],1,pc,pno)
    if exp is not None:
     try:value=self.eval(exp,pno)
     except Unresolved:value=0
     if mode=='rel':
      if pno==2:
       delta=value-(pc+1)
       if not -128<=delta<=127:raise ValueError(f'branch out of range: {delta} at ${pc-1:04X}')
       value=delta&255
      else:value=0
     size=1 if mode in ('rel','imm','zp','zpx','zpy','indx','indy') else 2
     pc=self.emit(value,size,pc,pno)
   except Exception as e:
    raise ValueError(f"{path}:{lno}: {raw}: {e}") from e
 def assemble(self,out):
  self.run(1);self.run(2)
  if not self.mem:raise ValueError('no data')
  low=min(self.mem);high=max(self.mem)
  if low<0x0801:raise ValueError('PRG start must be >= $0801')
  buf=bytes([low&255,low>>8])+bytes(self.mem.get(a,0) for a in range(low,high+1))
  Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_bytes(buf)
  return low,high,len(buf)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('-o','--output',required=True);p.add_argument('--symbols');a=p.parse_args()
 try:
  assembler=Assembler(a.source);lo,hi,n=assembler.assemble(a.output)
  if a.symbols:Path(a.symbols).write_text(''.join(f'{v:04X} {k}\n' for k,v in sorted(assembler.sym.items(),key=lambda x:x[1])))
  print(f'PASS: {a.output}: ${lo:04X}-${hi:04X}, {n} bytes (incl load addr), {len(assembler.sym)} symbols')
 except Exception as e:sys.exit(f'ASM ERROR: {e}')
