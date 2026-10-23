"""Independent scene selection and fresh island checkpoint contracts."""
import ctypes,subprocess,tempfile
from common import *
from build_selector import build as selector_build
class Selector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();p=Path(cls.tmp.name);cls.path=p
        for i in range(29):(p/f'SCENE{i+1:02d}.bin').write_bytes(b'MLI1'+bytes([4 if i%3 else 2]))
        cls.report=selector_build(p,p/'NGSELECT');cls.sym=cls.report['symbols'];cls.prg=p/'NGSELECT'
        stub=p/'state.c';stub.write_text('#include <stdint.h>\nuint8_t ng_state[128];\n')
        subprocess.run(['clang','-shared','-fPIC','-o',str(p/'selector.dylib'),str(ROOT/'src/gameplay/selector.c'),str(stub)],check=True,capture_output=True)
        cls.lib=ctypes.CDLL(str(p/'selector.dylib'));cls.lib.ng_select_island.argtypes=[ctypes.c_uint8]
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):self.cpu=CPU(self.prg)
    def branch(self,label,mode,index=0,key=None):
        c=self.cpu;s=self.sym;c.m[s['sel_mode']]=mode;c.m[s['sel_index']]=index;c.m[s['sel_tens']]=255
        c.pc=s[label]
        if key is not None:c.a=ord(key)
        for _ in range(1000):
            if c.pc==s['sel_menu']:return c.m[s['sel_mode']],c.m[s['sel_index']]
            c.step()
        self.fail('selection did not return to menu')
    def test_wraps_both_catalogs_without_selecting_nonexistent_scene(self):
        for mode,last in [(0,28),(1,27)]:
            self.assertEqual(self.branch('sel_previous',mode,0),(mode,last))
            self.assertEqual(self.branch('sel_next',mode,last),(mode,0))
    def test_two_digit_selection_and_mode_reset(self):
        c=self.cpu;s=self.sym;c.m[s['sel_mode']]=0;c.m[s['sel_tens']]=2;c.a=ord('9');c.pc=s['sel_input']
        for _ in range(100):
            if c.pc==s['sel_menu']:break
            c.step()
        self.assertEqual(c.m[s['sel_index']],28)
        self.assertEqual(self.branch('sel_game',0,28),(1,0))
        self.assertEqual(self.branch('sel_intro',1,27),(0,0))
    def test_patch_scenes_rebuild_their_own_full_background(self):
        self.assertEqual(self.report['scene_bases'],[i-i%3 for i in range(29)])
        self.assertEqual(self.prg.read_bytes()[:2],PRG.read_bytes()[:2])
        self.assertLess(self.report['overlay_end'],0x2000)
        at=2+0x2000-0x0801;self.assertEqual(self.prg.read_bytes()[at:],PRG.read_bytes()[at:])
    def test_opening_fire_press_must_be_released(self):
        c=self.cpu;s=self.sym;frozen=symbols();c.m[frozen['joy_raw']]=15;c.pc=s['sel_release_fire']
        for _ in range(40):c.step()
        self.assertLess(c.pc,s['sel_preview_wait']);self.assertEqual(c.m[frozen['ic_active']],0)
        c.m[frozen['joy_raw']]=31
        c.run_until(s['sel_preview_wait'],max_steps=100)
        self.assertEqual(c.m[frozen['ic_active']],1)
    def test_all_island_checkpoints_and_final_battle_reserves(self):
        state=(ctypes.c_uint8*128).in_dll(self.lib,'ng_state')
        for island in range(28):
            state[:]=bytes(128);self.assertEqual(self.lib.ng_select_island(island),1)
            self.assertEqual(state[12],island);self.assertEqual(state[123],0)
            pool=state[116]|state[117]<<8
            self.assertEqual(pool,100 if island==27 else 100+(island//3)*100)
            if island==27:
                self.assertEqual(bytes(state[42:50]),b'\xe8\x03'*4);self.assertEqual(state[118],100)
        before=bytes(state);self.assertEqual(self.lib.ng_select_island(28),0);self.assertEqual(bytes(state),before)
