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
        # Notification rendering is outside the rules contract. Returning from
        # this far UI entry leaves all rule memory and registers unchanged.
        from unicorn import UC_HOOK_CODE
        def notification(u,address,size,data):
            m=self.machine;sp=m.r('sp');ss=m.r('ss')
            ip,cs=struct.unpack('<HH',u.mem_read(ss*16+sp,4))
            m.w('sp',sp+4);m.w('cs',cs);m.w('ip',ip)
        entry=(self.machine.module_seg+0x1a17)*16+0x199d
        self.u.hook_add(UC_HOOK_CODE,notification,None,entry,entry)
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
    def apply(self,opcode,sector,request,recipe,army=None,alliances=None,retired=None,field_armies=None,owned=None,personality=None,plan=None):
        self.u.mem_write(self.base+SECTOR_BASE,bytes(sector))
        self.u.mem_write(self.base+0x4a00,bytes(recipe))
        self.u.mem_write(self.base+0x4982,bytes(recipe))
        self.u.mem_write(self.base+0x4a20,bytes(army or bytes(11)))
        self.u.mem_write(self.base+0x4cb8,bytes(army or bytes(11)))
        self.u.mem_write(self.base+0x9c,bytes(alliances or bytes([1,2,4,8])))
        self.word(0x2d16,struct.unpack_from('<H',request,30)[0])
        for f in range(4):
            self.word(0x2d38+f*2,(owned or bytes(4))[f])
            self.word(0x2d40+f*2,(retired or bytes(4))[f]);self.word(0x2d48+f*2,(field_armies or bytes(4))[f]);self.word(0x1cbc+f*2,0)
        self.word(0x1c78,struct.unpack_from("<H",request,14)[0]);self.word(0x1c74,1)
        self.word(0x2456,0)
        self.word(0x1c64,struct.unpack_from('<H',request,24)[0])
        self.u.mem_write(self.base+0x4a40,bytes(personality or bytes(56)));self.u.mem_write(self.base+0x4a80,bytes(plan or bytes(28)))
        self.word(0x9a28,0x4a40);self.word(0x9a24,0x4a80)
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
                 (0,0x5a9f),(0,0xcd19),(0,0x670b),(0,0x5b10),(0,0x6366),(0,0x68f4),(0x1471,0x33c),(0,0x6ec4),(0,0x6b6c),(0,0x74c8),(0xd24,0x1669),(0x11b9,0x1b40),(0xd24,0x39b1),(0x16b4,0x3156),(0xd24,0x3f9d),(0x1a17,0x1383),(0x1a17,0x12b4),(0x16b4,0x18f7),(0xd24,0x3d7f),(0x16b4,0x1ba9),(0x11b9,0x1262),(0x16b4,0xa60),(0x16b4,0x168a),(0x16b4,0x22a3),(0xd24,0x1582),(0x11b9,0x1c9c),(0x1471,0x278),(0x16b4,0x26ab),(0x16b4,0x6dd),(0x16b4,0xdb1),(0x16b4,0x1831)]
        if opcode in [18,20,28,29]:self.word(0x9a14,0x4a20)
        if opcode==54:self.word(0x9a10,0x4a20)
        if opcode in [57,60]:self.word(0x1c6c,struct.unpack_from("<H",request,6)[0])
        if opcode==20:self.word(0x9a18,struct.unpack_from('<H',request,24)[0])
        if opcode in [24,33,50]:self.word(0x1c6c,struct.unpack_from('<H',request,6)[0])
        if opcode==2:self.word(0x99f4,struct.unpack_from('<H',request,4)[0])
        if opcode==8:
            self.word(0x99f4,struct.unpack_from('<H',request,14)[0]);self.word(0x99f8,struct.unpack_from('<H',request,16)[0])
        if opcode==51:self.word(0x1c6c,struct.unpack_from("<H",request,14)[0])
        if opcode==39:
            self.word(0x245c,0);self.word(0x9a0c,struct.unpack_from("<H",request,4)[0])
        if opcode==38:
            owner=struct.unpack_from("<H",sector,0x3fe)[0];self.word(0x1cbc+owner*2,0)
        if opcode==47:
            for offset in [0x18f7,0x1a34,0x1ae7,0x1b97]:self.call(0x16b4,offset,near=True)
        elif opcode==49:
            self.word(0x9a0c,struct.unpack_from("<H",sector,0x404)[0])
            for offset in [0x1ba9,0x1d51,0x1ff4]:self.call(0x16b4,offset,near=True)
        elif opcode==50:
            self.call(0x11b9,0x1262);self.call(0,0xc54c,near=True)
        else:self.call(*entries[opcode],near=opcode in [14,15,24,25,30,31,32,33,34,35,37,38,39,43,51,52,53,57,58,59,60])
        self.recipe=bytes(self.u.mem_read(self.base+0x4982,10))
        self.army=bytes(self.u.mem_read(self.base+0x4a20,11))
        if opcode in [53,57]:self.army=bytes(self.u.mem_read(self.base+0x19ce,11))
        if opcode in [30,31]:self.army=bytes(self.u.mem_read(self.base+0x4cb8,11))
        self.army_left=self.word(0x4c94)
        self.saved=bytes(self.u.mem_read(self.base+0x1cbc,8))
        self.alliances=bytes(self.u.mem_read(self.base+0x9c,4))
        self.plan=bytes(self.u.mem_read(self.base+0x4a80,28))
        result=bytes(self.u.mem_read(self.base+SECTOR_BASE,SECTOR_BYTES))
        value=self.word(0x1cbc+owner*2)if opcode==38 else self.word(0x99f0)
        return result,value,self.word(0x3098),self.word(0x99f2),self.word(0x99f4)

    def route_mask(self,classes,source):
        self.u.mem_write(self.base+0x550a,bytes(36))
        self.u.mem_write(self.base+0x9c,bytes([1,2,4,8]));self.word(0x2d16,15)
        for i,kind in enumerate(classes):
            sector=bytearray(SECTOR_BYTES)
            struct.pack_into('<HH',sector,0x3fe,0 if kind==1 else 1,0)
            struct.pack_into('<H',sector,0x402,i);sector[0x448]=128 if kind else 0
            self.u.mem_write(self.base+SECTOR_BASE+i*SECTOR_BYTES,bytes(sector))
            self.word(0x553e+i*2,SECTOR_BASE+i*SECTOR_BYTES)
        self.word(0x9a10,SECTOR_BASE+source*SECTOR_BYTES);self.word(0x99f0,0)
        self.call(0xd24,0x39b1)
        visited=bytes(self.u.mem_read(self.base+0x552e,16))
        self.routes=bytes(4 if visited[i] else classes[i]for i in range(16))
        return sum(1<<i for i,v in enumerate(visited)if v)
