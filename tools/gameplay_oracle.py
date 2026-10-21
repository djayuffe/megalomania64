"""Bounded callable DOS gameplay oracle for differential native-port tests.

Only audited near/far entry points explicitly requested by the verifier execute.
No native DOS process, game input automation, or host file writes are exposed.
"""
import struct
from pathlib import Path
from trace_dos import Machine
from gameplay_data import extract, SECTOR_BASE, SECTOR_BYTES


class Oracle:
    def __init__(self,dos,out):
        self.rules=extract((Path(dos)/'MEGA.EXE').read_bytes())
        self.machine=Machine(dos,out)
        self.u=self.machine.uc
        self.base=self.machine.ds*16
    def word(self,address,value=None):
        if value is None:return struct.unpack('<H',self.u.mem_read(self.base+address,2))[0]
        self.u.mem_write(self.base+address,struct.pack('<H',value&65535))
    def call(self,segment,offset,near=False):
        m=self.machine
        for reg,value in [('ds',m.ds),('es',m.ds),('ss',0x9000),('sp',0xfefc),('cs',m.module_seg+segment),('ip',offset),('eflags',2)]:m.w(reg,value)
        target=0x800
        if near:
            m.w('sp',0xfefe);self.u.mem_write(0x9fefe,struct.pack('<H',0x800));target=(m.module_seg+segment)*16+0x800
        else:self.u.mem_write(0x9fefc,struct.pack('<HH',0x800,0))
        self.u.emu_start((m.module_seg+segment)*16+offset,target,count=2000000,timeout=5000000)
        if (m.r('cs'),m.r('ip'),m.r('sp'))!=(m.module_seg+segment if near else 0,0x800,0xff00):
            raise RuntimeError(f'original routine did not return: {segment:04x}:{offset:04x}')
    def initialize(self,island):
        age=self.rules['islands'][island]['start_age']
        self.word(0x1c64,island);self.word(0x1c6c,age);self.word(0x1c6e,min(age+3,9));self.word(0x99f0,age)
        self.call(0x1a17,0x964)
        return [bytes(self.u.mem_read(self.base+SECTOR_BASE+i*SECTOR_BYTES,SECTOR_BYTES))for i in range(16)]
    def apply(self,opcode,sector,request,recipe,army=None,alliances=None):
        self.u.mem_write(self.base+SECTOR_BASE,bytes(sector))
        self.u.mem_write(self.base+0x4a00,bytes(recipe))
        self.u.mem_write(self.base+0x4982,bytes(recipe))
        self.u.mem_write(self.base+0x4a20,bytes(army or bytes(11)))
        self.u.mem_write(self.base+0x4cb8,bytes(army or bytes(11)))
        self.u.mem_write(self.base+0x9c,bytes(alliances or bytes([1,2,4,8])))
        self.word(0x2d16,struct.unpack_from('<H',request,30)[0])
        self.word(0x1c78,0)
        self.word(0x9a10,SECTOR_BASE)
        self.word(0x99f0,struct.unpack_from('<H',request,2)[0])
        self.word(0x99f2,0)
        self.word(0x99f4,struct.unpack_from('<H',request,4)[0])
        self.word(0x99f8,struct.unpack_from('<H',request,6)[0])
        self.word(0x9a14,0x4a00)
        self.word(0x3098,struct.unpack_from('<H',request,10)[0])
        self.word(0x99fc,struct.unpack_from('<H',request,8)[0])
        self.word(0x2418,struct.unpack_from('<H',request,26)[0])
        self.word(0x1c6e,struct.unpack_from('<H',request,28)[0])
        entries=[(0xd24,0x2890),(0x11b9,0x1487),(0x11b9,0x1378),(0x11b9,0x1678),
                 (0xd24,0x2af1),(0xd24,0x2bd5),(0xd24,0x2def),(0x11b9,0xeb1),(0x11b9,0x11e8),
                 (0xd24,0x194b),(0x11b9,0x15d8),(0x11b9,0x183e),(0x1a17,0x599),
                 (0x1471,0x187),(0,0xce20),(0,0xc950),(0xd24,0x13d7),(0x1471,0),
                 (0xd24,0xf91),(0x1471,0xfcd),(0x1a17,0x165f),(0x1471,0x5de),
                 (0xd24,0x1bcd),(0xd24,0xe4e),(0,0x5e55),(0,0x6154),
                 (0x11b9,0x108c),(0xd24,0x2336),(0x11b9,0x1e18),(0x11b9,0x1f93),
                 (0,0x5a9f),(0,0xcd19),(0,0x670b)]
        if opcode in [18,20,28,29]:self.word(0x9a14,0x4a20)
        if opcode==20:self.word(0x9a18,struct.unpack_from('<H',request,24)[0])
        if opcode==24:self.word(0x1c6c,struct.unpack_from('<H',request,6)[0])
        if opcode==2:self.word(0x99f4,struct.unpack_from('<H',request,4)[0])
        if opcode==8:
            self.word(0x99f4,struct.unpack_from('<H',request,14)[0]);self.word(0x99f8,struct.unpack_from('<H',request,16)[0])
        self.call(*entries[opcode],near=opcode in [14,15,24,25,30,31,32])
        self.recipe=bytes(self.u.mem_read(self.base+0x4982,10))
        self.army=bytes(self.u.mem_read(self.base+0x4a20,11))
        if opcode in [30,31]:self.army=bytes(self.u.mem_read(self.base+0x4cb8,11))
        self.army_left=self.word(0x4c94)
        result=bytes(self.u.mem_read(self.base+SECTOR_BASE,SECTOR_BYTES))
        return result,self.word(0x99f0),self.word(0x3098),self.word(0x99f2),self.word(0x99f4)
