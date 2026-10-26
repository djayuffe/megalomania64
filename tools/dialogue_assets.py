"""Private conversion of DOS dialogue descriptors, original faces and voices."""
import json
import struct
import tempfile
from pathlib import Path
from lzhuf import decompress
from native_graphics import planar_tile, resource, palette
from make_speech import convert
from scene_format import pack
from orig_convert import C64

BASES = (8, 22, 79, 15)
VOICE_FIRST = 20

def descriptors(exe):
    ds = 0x22f00
    rows = []
    for faction, base in enumerate(BASES):
        pointer = struct.unpack_from('<H', exe, ds+0x2db8+faction*2)[0]
        desc = struct.unpack_from('<8H', exe, ds+pointer)
        if desc[0] != 0xaf84 or desc[6:] != (160, 40):
            raise ValueError('unsupported original portrait descriptor')
        voices = []
        for kind in range(3):
            at = struct.unpack_from('<H', exe, ds+0xad74+(base+kind)*2)[0]
            voices.append(exe[ds+at:].split(b'\0', 1)[0].decode('ascii'))
        rows.append((desc, voices))
    return rows

def face(raw, desc, colors):
    _, offset, _, _, w, h, pitch, _ = desc
    pixels = planar_tile(raw, offset, w, h, pitch)
    # Preserve the complete source face in a 32x32 hires character portrait.
    rgb = [[colors[pixels[min(h-1,y*h//32)][min(w-1,x*w//32)]] for x in range(32)] for y in range(32)]
    glyphs = bytearray(); inks = bytearray()
    for cy in range(4):
        for cx in range(4):
            cell = [rgb[cy*8+y][cx*8+x] for y in range(8) for x in range(8)]
            distances = [[sum((p[k]-c[k])**2 for k in range(3)) for c in C64] for p in cell]
            ink = min(range(1,16), key=lambda c:sum(min(d[0],d[c]) for d in distances))
            glyphs.extend(sum((distances[y*8+x][ink]<distances[y*8+x][0])<<(7-x) for x in range(8)) for y in range(8))
            inks.append(ink)
    return bytes(glyphs+inks)

def build(dos, files):
    exe = (dos/'MEGA.EXE').read_bytes()
    icons = resource(dos/'ICONS.DAT'); colors = palette(dos/'ISLANDS.LBM')
    report = []
    with tempfile.TemporaryDirectory() as folder:
        decoded = Path(folder)/'voice'
        for faction, (desc, voices) in enumerate(descriptors(exe)):
            portrait=face(icons,desc,colors)
            (files/f'NFAC{faction:02d}').write_bytes(b'NGH1'+pack(portrait[:128])+portrait[128:])
            for kind, source in enumerate(voices):
                target = files/f'NSND{VOICE_FIRST+faction*3+kind:02d}'
                path = dos/source
                row = dict(faction=faction,kind=kind,dialogue_id=BASES[faction]+kind,source=source,file=target.name,available=path.is_file())
                if path.is_file():
                    raw=path.read_bytes();decoded.write_bytes(raw if raw.startswith(b'FORM') else decompress(raw))
                    pcm,_=convert(decoded)
                    if not pcm or len(pcm)>4346:raise ValueError(f'dialogue voice exceeds sample window: {source}')
                    target.write_bytes(b'NGS1'+struct.pack('<HB',len(pcm)*2,1)+pack(pcm))
                    row['nibbles']=len(pcm)*2
                else:
                    # An empty, valid speech stream signals unavailable audio.
                    target.write_bytes(b'NGS1'+struct.pack('<HB',0,1))
                report.append(row)
    (files/'dialogue.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
