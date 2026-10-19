"""Shared fixtures for the Mega-Lo-Mania 64 6502 model tests."""
import subprocess, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
from cpu6502 import CPU

PRG=ROOT/'dist/MegaLoMania64.prg'

def build():
    subprocess.run([sys.executable,str(ROOT/'tools/asm6502.py'),str(ROOT/'src/main.asm'),'-o',str(PRG),
                    '--symbols',str(ROOT/'dist/symbols.txt')],cwd=ROOT,check=True,capture_output=True)

def symbols():
    return {v:int(a,16) for a,v in (ln.split() for ln in (ROOT/'dist/symbols.txt').read_text().splitlines())}

def boot(cpu,sym,pal=True,max_steps=3000000):
    """Power-on path: start -> title screen -> main_loop, with raster IRQs and a key press."""
    cpu.m[0x02a6]=1 if pal else 0
    cpu.pc=sym['start']
    seen=[0]
    def press(c):
        if c.pc==sym['title_wait']:
            seen[0]+=1
            if seen[0]==12:c.key=ord(' ')
    cpu.run_until(sym['main_loop'],max_steps=max_steps,on_pc=press)
    return cpu

class GameCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build();cls.sym=symbols()
    def setUp(self):
        self.cpu=CPU(PRG)
        self.cpu.call(self.sym['new_game'])
    def state(self,name,idx=None):return self.cpu.m[self.sym[name]+(idx or 0)]
    def put(self,name,v,idx=None):self.cpu.m[self.sym[name]+(idx or 0)]=v
    def call(self,name):return self.cpu.call(self.sym[name])
    def press(self,key):
        self.cpu.key=ord(key) if isinstance(key,str) else key
        self.call('read_keys')
    def screen(self,row,col=0,n=40):
        return bytes(self.cpu.m[0x400+row*40+col+i] for i in range(n)).decode('latin1')
    def irq_on(self):
        """Install the IRQ engine exactly as start does (CLI at the end)."""
        self.call('irq_install')
        self.assertFalse(self.cpu.p&4)
    def fill(self,name,values):
        for i,v in enumerate(values):self.put(name,v,i)
