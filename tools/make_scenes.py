#!/usr/bin/env python3
"""Build full-height scrolling credits and staged stories from audited DOS assets."""
import argparse
import json
from pathlib import Path
from PIL import Image
from orig_import import load_ilbm
from scene_format import encode, encode_credit, encode_story_patch, decode
from intro_timeline import inspect, CREDIT_STEPS, STORY_PHASES, STORY_RETRACES

ROOT = Path(__file__).resolve().parents[1]


def image(path):
    w,h,palette,rows = load_ilbm(path)
    im = Image.new('RGB',(w,h))
    im.putdata([palette[index] for row in rows for index in row])
    return im


def credit_tiles(im):
    """Hires character tiles with black background and a best-fit cell ink.

    The original 320x600 canvas is retained. No rescaling or centering occurs.
    Each card must fit the VIC's 256-character alphabet or the build fails.
    """
    import numpy as np
    from vic_bitmap import PALETTE, perceptual
    pixels=np.asarray(im.convert('RGB'))
    if pixels.shape != (600,320,3):raise ValueError('credit canvas must be 320x600')
    cells=pixels.reshape(75,8,40,8,3).transpose(0,2,1,3,4).reshape(3000,64,3)
    distance=((perceptual(cells)[:,:,None,:]-PALETTE[None,None,:,:])**2).sum(axis=3)
    neutral=(cells.max(axis=2)-cells.min(axis=2))<=3
    distance+=neutral[:,:,None]*np.array([c not in (0,1,11,12,15) for c in range(16)])[None,None,:]
    error=np.minimum(distance,distance[:,:,[0]]).sum(axis=1)
    inks=error.argmin(axis=1)
    glyphs=[bytes(8)];lookup={glyphs[0]:0};tilemap=bytearray();colors=bytearray()
    for i,ink in enumerate(inks):
        bits=(distance[i,:,ink]<distance[i,:,0]).reshape(8,8)
        glyph=bytes(sum(int(v)<<(7-x) for x,v in enumerate(row)) for row in bits)
        if glyph not in lookup:
            lookup[glyph]=len(glyphs);glyphs.append(glyph)
        tilemap.append(lookup[glyph]);colors.append(int(ink))
    if len(glyphs)>256:raise ValueError('credit exceeds character RAM')
    return b''.join(glyphs).ljust(2048,b'\0'),bytes(tilemap),bytes(colors),len(glyphs)


def build(decoded,dos,out):
    from vic_bitmap import convert, mixed_story
    decoded,dos,out=Path(decoded),Path(dos),Path(out)
    out.mkdir(parents=True,exist_ok=True)
    evidence=inspect((dos/'MEGA.EXE').read_bytes())
    (out/'intro_evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    manifest=[]
    def save(data,preview,source,**details):
        name=f'SCENE{len(manifest)+1:02d}'
        decode(data);(out/(name+'.bin')).write_bytes(data)
        preview.save(out/(name+'.png'))
        manifest.append(dict(file=name,source=source,bytes=len(data),**details))
    # Original order: four stories, each showing successive 39-pixel text strips.
    for i,phases in enumerate(STORY_PHASES,1):
        original=image(decoded/f'V{i}E.DAT')
        for phase in range(phases):
            shown=original.crop((0,0,320,200))
            if phase:
                y=200+(phase-1)*39
                shown.paste(original.crop((0,y,320,y+39)),(0,161))
            bitmap,screen,color,preview=mixed_story(shown,rows=20)
            payload=(encode_story_patch(bitmap[6400:],screen[800:],color[800:],STORY_RETRACES) if phase
                     else encode(bitmap,screen,color,multicolor=2,frames=STORY_RETRACES))
            save(payload,
                 preview,f'V{i}E.DAT',phase=phase,frames=STORY_RETRACES,multicolor=2)
    # VGA line-compare preserves the logo below the 160-pixel credit viewport.
    logo=image(decoded/'VH.DAT').crop((0,0,320,40))
    canvas=Image.new('RGB',(320,200));canvas.paste(logo,(0,160))
    lb,ls,_,_=convert(canvas)
    for i,steps in enumerate(CREDIT_STEPS,5):
        original=image(decoded/f'V{i}E.DAT')
        charset,cells,colors,glyphs=credit_tiles(original)
        save(encode_credit(charset,cells,colors,lb[6400:],ls[800:],steps),
             original,f'V{i}E.DAT',steps=steps,multicolor=3,glyphs=glyphs)
    data=encode((ROOT/'assets/intro_bitmap.bin').read_bytes(),
                (ROOT/'assets/intro_screen.bin').read_bytes(),
                (ROOT/'assets/intro_color.bin').read_bytes(),multicolor=True,frames=1)
    (out/'TITLE.bin').write_bytes(data)
    (out/'scenes.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'{len(manifest)} original intro stages + TITLE: {sum(x["bytes"] for x in manifest)+len(data)} bytes')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--decoded',required=True,type=Path)
    p.add_argument('--dos',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();build(a.decoded,a.dos,a.out)
