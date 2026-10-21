#!/usr/bin/env python3
"""Build the native integration disk privately from version-checked owner content."""
import argparse,json,re,struct,subprocess,sys
from pathlib import Path
from asm6502 import Assembler
from gameplay_data import extract,SECTOR_BYTES
from native_world import encode,SLOT
from scene_format import pack,unpack

ROOT=Path(__file__).resolve().parents[1]

def run(args):
    r=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,errors='replace')
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)

def assemble(path,out,constants=None):
    a=Assembler(path);a.sym.update(constants or {});a.assemble(out);return a

def record(desc,age,classes):
    b=bytearray(SECTOR_BYTES)
    def w(at,n):struct.pack_into('<H',b,at,n)
    def d(at,n):struct.pack_into('<I',b,at,n)
    w(10,65535);w(0x3fe,4);w(0x402,desc['index']);w(0x418,age);w(0x3fc,456)
    w(0xbe,65535);w(0xd2,65535);w(0x43e,65535);w(0x440,65535)
    for at in [0xb4,0xc6,0xda]:d(at,0xffffffff)
    for base,count in [(12,4),(0x6c,3)]:
        for k in range(count):d(base+k*24+6,0xffffffff)
    b[0x3b8:0x3c2]=bytes([255]*10);b[0x448]=128 if desc['land']else 0
    for k in range(4):
        d(0x136+k*16,0xffffffff);w(0x140+k*16,65535)
    for k,v in enumerate(desc['deposits']):
        e=v['element'];w(0x140+k*16,65535 if e==255 else e);w(0x142+k*16,v['amount'])
        if e!=255 and classes[e]==0:w(0x174+e*2,v['amount'])
    return b

def picture(data):
    """Make a 48x16 hires character picture from the converted original atlas.

    Each character retains its dominant source colour; no runtime bitmap bank
    overlaps the world. The source's 2-bit horizontal pixels are doubled.
    """
    if len(data)!=135 or data[:4]!=b'MLC1':raise ValueError('invalid island card')
    glyphs=bytearray();inks=[]
    for cy in range(2):
        for cx in range(6):
            pixels=[]
            for y in range(8):
                row=[]
                for x in range(8):
                    px=cx*8+x;half=px//24;bit=11-(px%24)//2
                    at=7+half*64+(cy*8+y+2)*3
                    code=(int.from_bytes(data[at:at+3],'big')>>(bit*2))&3
                    row.append(0 if not code else data[3+code])
                pixels.append(row)
            counts={c:sum(row.count(c)for row in pixels)for c in data[4:7]}
            ink=max(counts,key=counts.get);inks.append(ink)
            glyphs.extend(sum((c!=0)<<(7-x)for x,c in enumerate(row))for row in pixels)
    return bytes(glyphs),inks

def build(dos,content,cc65,out,disk):
    out=out.resolve();disk=disk.resolve()
    if out.is_relative_to(ROOT)or disk.is_relative_to(ROOT):raise ValueError('native content must stay outside checkout')
    out.mkdir(parents=True,exist_ok=True);files=out/'files';files.mkdir(exist_ok=True)
    rules=extract((dos/'MEGA.EXE').read_bytes())
    support=assemble(ROOT/'src/gameplay/hardware.asm',out/'support.prg',dict(RUNTIME_MAIN=0x8000,ZP_STACK=2))
    if support.sym['native_key_end']>0x3300:raise ValueError('joystick code overlaps control data')
    if support.sym['support_loader_end']>0x1000 or support.sym['support_end']>0x2960:raise ValueError('native support overlaps rules code')
    exports={f'_{name}':support.sym[name]for name in ['hw_open','hw_read','hw_close','hw_key','hw_frames','hw_play','hw_error','clip_voice']}
    cfg='MEMORY { ZP: start=$0002,size=$001a,type=rw; RAM: start=$7000,size=$1000,type=rw; LOW: start=$1000,size=$1800,type=rw,file="%O.low"; HIGH: start=$8000,size=$4000,type=rw,file=%O; EXTRA: start=$2960,size=$07e0,type=rw,file="%O.extra"; GFX: start=$6900,size=$0700,type=rw,file="%O.gfx"; TEXT: start=$3400,size=$0300,type=rw,file="%O.text"; }\n'
    cfg+='SEGMENTS { ZEROPAGE:load=ZP,type=zp; STARTUP:load=HIGH,type=ro; CODE:load=HIGH,type=ro; LOWCODE:load=LOW,type=ro; GRAPHICS:load=GFX,type=ro; RUNTIME:load=EXTRA,type=ro; UIRODATA:load=TEXT,type=ro; RODATA:load=HIGH,type=ro; DATA:load=HIGH,type=rw; BSS:load=RAM,type=bss,define=yes; }\n'
    cfg+='SYMBOLS {'+''.join(f'{name}:type=export,value=${value:04x};'for name,value in exports.items())+'}\n'
    (out/'runtime.cfg').write_text(cfg)
    objects=[]
    for name in ['core','world','runtime']:
        run([cc65/'bin/cc65','-t','none','-O','-Cl','-o',out/(name+'.s'),ROOT/f'src/gameplay/{name}.c'])
        run([cc65/'bin/ca65','-t','none','-o',out/(name+'.o'),out/(name+'.s')]);objects.append(out/(name+'.o'))
    run([cc65/'bin/ca65','-t','none','-o',out/'entry.o',ROOT/'src/gameplay/entry.s'])
    run([cc65/'bin/ld65','-C',out/'runtime.cfg','-m',out/'runtime.map','-Ln',out/'runtime.lbl','-o',out/'runtime.bin',*objects,out/'entry.o',cc65/'lib/none.lib'])
    labels={line.split()[2].lstrip('.'):int(line.split()[1],16)for line in(out/'runtime.lbl').read_text().splitlines()if line.startswith('al ')}
    support=assemble(ROOT/'src/gameplay/hardware.asm',files/'NGSUPP',dict(RUNTIME_MAIN=labels['_runtime_main'],ZP_STACK=labels['c_sp']))
    for name,suffix,address in [('NGLOW','.low',0x1000),('NGHIGH','',0x8000),('NGEXTRA','.extra',0x2960),('NGDRAW','.gfx',0x6900),('NGTEXT','.text',0x3400)]:
        (files/name).write_bytes(struct.pack('<H',address)+(out/('runtime.bin'+suffix)).read_bytes())
    boot=assemble(ROOT/'src/gameplay/boot.asm',files/'NGSTART')
    data=bytearray(b'NGR1')
    for values in [rules['element_classes']]:data+=bytes(values)
    for v in rules['buildings']:data+=struct.pack('<12H',*(v['health']+[v['turrets'],v['turret_offset']]))
    for group in rules['design_patterns']:
        for pat in group:data+=bytes([len(pat)]+[v for pair in pat for v in pair]+[0]*(8-len(pat)*2))
    data+=bytes(v for pair in rules['material_groups']for v in pair)
    for name in ['research_complexity','manufacture_complexity','research_points','technology_points']:
        data+=struct.pack('<'+'H'*len(rules[name]),*rules[name])
    for name in ['army_rules','defence_rules']:
        for field in ['health','strength','crew']:data+=struct.pack('<'+'H'*len(rules[name][field]),*rules[name][field])
    data+=bytes([1,2,4,8]);(files/'NGTABLE').write_bytes(data)
    for island in rules['islands']:
        raw=b''.join(encode(record(s,island['start_age'],rules['element_classes']),island['start_age'],island['max_age'])for s in island['sectors'])
        assert len(raw)==SLOT*16
        header=b'NGW2'+bytes([island['start_age'],island['max_age']])+bytes(s['tile']for s in island['sectors'])
        card,inks=picture((content/f'ISL{island["index"]+1:02d}.bin').read_bytes())
        header+=pack(card)+bytes(inks)
        (files/f'NMAP{island["index"]+1:02d}').write_bytes(header+pack(raw))
    army=(ROOT/'assets/orig/army_frames.bin').read_bytes();builds=(ROOT/'assets/orig/build_icons.bin').read_bytes()
    for age in range(10):(files/f'NSPR{age:02d}').write_bytes(b'NGP1'+pack(army[age*256:age*256+256]+builds[age*64:age*64+64]))
    effects=(content/'EFFECTS.bin').read_bytes();part,at=unpack(effects,9000,4);tail,at=unpack(effects,3072,at);pcm=part+tail
    samples=json.loads((ROOT/'assets/orig/samples.json').read_text())['samples']
    for i,v in enumerate(samples):
        n=v['full_nibbles'];raw=pcm[v['full_offset']:v['full_offset']+(n+1)//2]
        (files/f'NSND{i:02d}').write_bytes(b'NGS1'+struct.pack('<HB',n,0)+pack(raw))
    speech=(content/'SPEECH.bin').read_bytes();part,at=unpack(speech,0x3380,36);tail,at=unpack(speech,0x1ffa,at);pcm=part+tail;offset=0
    for i in range(8):
        address,n=struct.unpack_from('<HH',speech,4+i*4);size=(n+1)//2
        if size>4346:raise ValueError('voice exceeds cache')
        (files/f'NSND{i+11:02d}').write_bytes(b'NGS1'+struct.pack('<HB',n,1)+pack(pcm[offset:offset+size]));offset+=size
    disk.parent.mkdir(parents=True,exist_ok=True)
    command=['c1541','-format','megalomania64,64','d81',disk,'-attach',disk,'-write',ROOT/'dist/MegaLoMania64.prg','megalomania']
    for path in sorted(content.glob('*.bin')):
        if path.stem in ['TITLE','SPEECH','MUSIC','MUSICG','EFFECTS']or path.stem.startswith(('SCENE','ISL')):command+=['-write',path,path.stem.lower()]
    for path in sorted(files.iterdir()):command+=['-write',path,path.name.lower()]
    run(command)
    immutable=int(re.search(r'^DATA\s+([0-9A-F]+)',(out/'runtime.map').read_text(),re.M)[1],16)-0x8000
    report=dict(immutable_high_bytes=immutable,disk=str(disk),slot_bytes=SLOT,world_bytes=SLOT*16,native_files=len(list(files.iterdir())),runtime_main=labels['_runtime_main'],hardware={name:support.sym[name]for name in ['hw_key','hw_frames','hw_play','native_frames','mu_ready','smp_left']},boot_error=boot.sym['boot_error'],limitations=['development native integration; full battle scheduler and AI not yet ported'])
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dos',type=Path,required=True);p.add_argument('--content',type=Path,required=True);p.add_argument('--cc65',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--disk',type=Path,required=True)
    a=p.parse_args();build(a.dos,a.content,a.cc65,a.out,a.disk)
