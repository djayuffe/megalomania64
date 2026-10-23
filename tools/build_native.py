#!/usr/bin/env python3
"""Build the native integration disk privately from version-checked owner content."""
import argparse,json,re,struct,subprocess,sys
from pathlib import Path
from asm6502 import Assembler
from gameplay_data import extract,SECTOR_BYTES
from native_world import encode,SLOT
from scene_format import pack,unpack
from check_intro import verify as verify_intro
from build_selector import build as build_selector
from native_graphics import terrain_tiles,resource,palette,convert as terrain_convert

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
    verify_intro(content)
    out=out.resolve();disk=disk.resolve()
    if out.is_relative_to(ROOT)or disk.is_relative_to(ROOT):raise ValueError('native content must stay outside checkout')
    out.mkdir(parents=True,exist_ok=True);files=out/'files';files.mkdir(exist_ok=True)
    exe=(dos/'MEGA.EXE').read_bytes();rules=extract(exe)
    terrain=terrain_tiles(exe,resource(dos/'SMALLMAP.DAT'));colors=palette(dos/'ISLANDS.LBM')
    support=assemble(ROOT/'src/gameplay/hardware.asm',out/'support.prg',dict(RUNTIME_MAIN=0x8000,ZP_STACK=2))
    if support.sym['native_key_end']>0x3300:raise ValueError('joystick code overlaps control data')
    if support.sym['support_loader_end']>0x1000 or support.sym['support_end']>0x2b00:raise ValueError('native support overlaps rules code')
    exports={f'_{name}':support.sym[name]for name in ['hw_open','hw_read','hw_close','hw_key','hw_frames','hw_play','hw_error','clip_voice','hw_store','hw_restore','hw_shadow','hw_crc','hw_audio_busy']}
    exports['_hw_eof']=support.sym['ld_eof']
    cfg='MEMORY { ZP: start=$0002,size=$001a,type=rw; RAM: start=$7000,size=$1000,type=rw; LOW: start=$1000,size=$1700,type=rw,file="%O.low"; HIGH: start=$8000,size=$4200,type=rw,file=%O; EXTRA: start=$2b00,size=$0640,type=rw,file="%O.extra"; CAMP: start=$ef00,size=$10fa,type=rw,file="%O.camp"; INTERFACE: start=$ef00,size=$10fa,type=rw,file="%O.ui"; MILITARY: start=$ef00,size=$10fa,type=rw,file="%O.military"; DIPLOMACY: start=$ef00,size=$10fa,type=rw,file="%O.diplomacy"; STRATEGY: start=$ef00,size=$10fa,type=rw,file="%O.strategy"; TACTICS: start=$ef00,size=$10fa,type=rw,file="%O.tactics"; AI: start=$ef00,size=$10fa,type=rw,file="%O.ai"; RARE: start=$ef00,size=$10fa,type=rw,file="%O.rare"; BANK: start=$d400,size=$1b00,type=rw,file="%O.bank"; GFX: start=$6900,size=$0700,type=rw,file="%O.gfx"; AUX: start=$0800,size=$0100,type=rw,file="%O.aux"; TEXT: start=$3400,size=$0300,type=rw,file="%O.text"; }\n'
    cfg+='SEGMENTS { ZEROPAGE:load=ZP,type=zp; STARTUP:load=HIGH,type=ro; CODE:load=HIGH,type=ro; BATTLE:load=BANK,type=ro; RARE:load=RARE,type=ro; AI:load=AI,type=ro; TACTICS:load=TACTICS,type=ro; STRATEGY:load=STRATEGY,type=ro; DIPLOMACY:load=DIPLOMACY,type=ro; MILITARY:load=MILITARY,type=ro; INTERFACE:load=INTERFACE,type=ro; CAMPAIGN:load=CAMP,type=ro; LOWCODE:load=LOW,type=ro; GRAPHICS:load=GFX,type=ro; RUNTIME:load=EXTRA,type=ro; AUXCODE:load=AUX,type=ro; UIRODATA:load=TEXT,type=ro; RODATA:load=HIGH,type=ro; DATA:load=HIGH,type=rw; BSS:load=RAM,type=bss,define=yes; }\n'
    cfg+='SYMBOLS {'+''.join(f'{name}:type=export,value=${value:04x};'for name,value in exports.items())+'}\n'
    (out/'runtime.cfg').write_text(cfg)
    objects=[]
    for name in ['core','ai','tactics','military','strategy','diplomacy','selector','world','game','campaign','interface','runtime']:
        run([cc65/'bin/cc65','-t','none','-O',*(['-Cl']if name not in ['military','interface','strategy','diplomacy']else[]),'-D','NATIVE_GAME=1','-o',out/(name+'.s'),ROOT/f'src/gameplay/{name}.c'])
        run([cc65/'bin/ca65','-t','none','-o',out/(name+'.o'),out/(name+'.s')]);objects.append(out/(name+'.o'))
    run([cc65/'bin/ca65','-t','none','-o',out/'entry.o',ROOT/'src/gameplay/entry.s'])
    run([cc65/'bin/ld65','-C',out/'runtime.cfg','-m',out/'runtime.map','-Ln',out/'runtime.lbl','-o',out/'runtime.bin',*objects,out/'entry.o',cc65/'lib/none.lib'])
    labels={line.split()[2].lstrip('.'):int(line.split()[1],16)for line in(out/'runtime.lbl').read_text().splitlines()if line.startswith('al ')}
    support=assemble(ROOT/'src/gameplay/hardware.asm',files/'NGSUPP',dict(RUNTIME_MAIN=labels['_runtime_main'],ZP_STACK=labels['c_sp']))
    for name,suffix,address in [('NGLOW','.low',0x1000),('NGHIGH','',0x8000),('NGEXTRA','.extra',0x2b00),('NGDRAW','.gfx',0x6900),('NGTEXT','.text',0x3400)]:
        (files/name).write_bytes(struct.pack('<H',address)+(out/('runtime.bin'+suffix)).read_bytes())
    boot=assemble(ROOT/'src/gameplay/boot.asm',files/'NGSTART')
    selector=build_selector(content,files/'NGSELECT')
    aux=(out/'runtime.bin.aux').read_bytes();(files/'NGAUX').write_bytes(b'NGA1'+struct.pack('<H',len(aux))+pack(aux))
    bank=(out/'runtime.bin.bank').read_bytes()
    (files/'NGCODE').write_bytes(b'NGC1'+struct.pack('<H',len(bank))+pack(bank))
    ui=(out/'runtime.bin.ui').read_bytes();(files/'NGUI').write_bytes(b'NGU1'+struct.pack('<H',len(ui))+pack(ui))
    military=(out/'runtime.bin.military').read_bytes();(files/'NGARMY').write_bytes(b'NGA2'+struct.pack('<H',len(military))+pack(military))
    diplomacy=(out/'runtime.bin.diplomacy').read_bytes();(files/'NGDIPLO').write_bytes(b'NGD1'+struct.pack('<H',len(diplomacy))+pack(diplomacy))
    strategy=(out/'runtime.bin.strategy').read_bytes();(files/'NGSTRAT').write_bytes(b'NGS2'+struct.pack('<H',len(strategy))+pack(strategy))
    tactics=(out/'runtime.bin.tactics').read_bytes();(files/'NGTACT').write_bytes(b'NGT1'+struct.pack('<H',len(tactics))+pack(tactics))
    ai=(out/'runtime.bin.ai').read_bytes();(files/'NGAI').write_bytes(b'NGI1'+struct.pack('<H',len(ai))+pack(ai))
    camp=(out/'runtime.bin.camp').read_bytes();(files/'NGCAMP').write_bytes(b'NGY1'+struct.pack('<H',len(camp))+pack(camp))
    rare=(out/'runtime.bin.rare').read_bytes();(files/'NGRARE').write_bytes(b'NGX1'+struct.pack('<H',len(rare))+pack(rare))
    data=bytearray(b'NGR4')
    for values in [rules['element_classes']]:data+=bytes(values)
    for v in rules['buildings']:data+=struct.pack('<12H',*(v['health']+[v['turrets'],v['turret_offset']]))
    for group in rules['design_patterns']:
        for pat in group:data+=bytes([len(pat)]+[v for pair in pat for v in pair]+[0]*(8-len(pat)*2))
    data+=bytes(v for pair in rules['material_groups']for v in pair)
    for name in ['research_complexity','manufacture_complexity','research_points','technology_points']:
        data+=struct.pack('<'+'H'*len(rules[name]),*rules[name])
    for name in ['army_rules','defence_rules']:
        for field in ['health','strength','crew']:data+=struct.pack('<'+'H'*len(rules[name][field]),*rules[name][field])
    data+=struct.pack('<5H',*rules['combat_rules']);data+=struct.pack('<10H',*rules['shield_rules']);data+=b''.join(struct.pack('<10H',*v)for v in rules['repair_caps']);data+=bytes([1,2,4,8]);data+=bytes(v for row in rules['deployment_orders']for v in row);data+=b''.join(struct.pack('<28H',*row)for row in rules['personalities']);(files/'NGTABLE').write_bytes(data)
    for island in rules['islands']:
        raw=b''.join(encode(record(s,island['start_age'],rules['element_classes']),island['start_age'],island['max_age'])for s in island['sectors'])
        assert len(raw)==SLOT*16
        header=b'NGW4'+bytes([island['start_age'],island['max_age'],island['factions']])+struct.pack('<H',island['deployment_people'])+bytes(s['tile']for s in island['sectors'])
        card,inks=picture((content/f'ISL{island["index"]+1:02d}.bin').read_bytes())
        header+=pack(card)+bytes(inks)
        (files/f'NMAP{island["index"]+1:02d}').write_bytes(header+pack(raw))
        font,mapping,inks,used=terrain_convert(terrain,[s['tile']for s in island['sectors']],colors,(ROOT/'assets/charset.bin').read_bytes(),card)
        (files/f'NART{island["index"]+1:02d}').write_bytes(b'NGF1'+pack(font)+mapping+inks)
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
    for path in sorted(files.iterdir()):
        if path.suffix!='.json':command+=['-write',path,path.name.lower()]
    run(command)
    immutable=int(re.search(r'^DATA\s+([0-9A-F]+)',(out/'runtime.map').read_text(),re.M)[1],16)-0x8000
    segments={name:dict(start=int(start,16),end=int(end,16),bytes=int(size,16))for name,start,end,size in re.findall(r'^([A-Z]+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+', (out/'runtime.map').read_text(),re.M)}
    report=dict(immutable_high_bytes=immutable,disk=str(disk),slot_bytes=SLOT,world_bytes=SLOT*16,native_files=sum(p.suffix!=".json"for p in files.iterdir()),runtime_main=labels['_runtime_main'],hardware={name:support.sym[name]for name in ['hw_key','hw_frames','hw_play','native_frames','mu_ready','smp_left','smp_rd','sample_finished','io_frames']},boot_error=boot.sym['boot_error'],
                selector={k:selector[k]for k in ["file","entry","intro_scenes","gameplay_islands","frozen_entry_sha256"]},intro_frozen=True,intro_retained_bytes=0,cleared_intro_ram_bytes=0x10000-0x900,reclaimed_bootstrap_bytes=256,
                game_owned_ram=dict(start=0x800,end=0xffff,bytes=0xf800),segments=segments,
                overlays=['NGRARE, NGCAMP, NGAI, NGTACT, NGARMY, NGUI, NGSTRAT and NGDIPLO share EF00-FFF9 with audio; resident wrappers switch overlays after leaf routines return'],
                limitations=['Deployment interaction timing and dialogue presentation remain C64 adaptations; negotiation decisions, expedition, roaming, demobilization, formation, retreat, home reinforcement, economy, reachability, defence/repair and deployment counts/orders are translated; human campaign balance, interface fidelity and physical hardware remain unverified'])
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dos',type=Path,required=True);p.add_argument('--content',type=Path,required=True);p.add_argument('--cc65',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--disk',type=Path,required=True)
    a=p.parse_args();build(a.dos,a.content,a.cc65,a.out,a.disk)
