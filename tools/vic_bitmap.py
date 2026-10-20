"""Deterministic VIC-II bitmap quantization using perceptual colour error.

Hires uses the best pair of the 16 C64 colours in each 8x8 cell. Multicolour
uses a shared background and the best three additional colours per 4x8 cell.
"""
from itertools import combinations
import numpy as np
from PIL import Image
from orig_convert import C64


def perceptual(rgb):
    rgb=np.asarray(rgb,dtype=np.float64)/255
    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    lms=linear@np.array([[.4122214708,.5363325363,.0514459929],[.2119034982,.6806995451,.1073969566],[.0883024619,.2817188376,.6299787005]]).T
    return np.cbrt(lms)@np.array([[.2104542553,.7936177850,-.0040720468],[1.9779984951,-2.4285922050,.4505937099],[.0259040371,.7827717662,-.8086757660]]).T

PALETTE=perceptual(C64)
PAIRS=np.array(list(combinations(range(16),2)))
TRIPLES=np.array(list(combinations(range(1,16),3)))


def convert(im,multicolor=False):
    im=im.convert('RGB').resize((320,200),Image.Resampling.LANCZOS)
    pixels=np.asarray(im)
    if multicolor:
        # Area average pixel pairs before mapping to avoid horizontal aliasing.
        pixels=pixels.reshape(200,160,2,3).mean(axis=2)
    width=4 if multicolor else 8
    cells=pixels.reshape(25,8,40,width,3).transpose(0,2,1,3,4).reshape(1000,8*width,3)
    rgb=perceptual(cells)
    distance=((rgb[:,:,None,:]-PALETTE[None,None,:,:])**2).sum(axis=3)
    # Neutral artwork/text must stay neutral; RGB brightness gaps otherwise
    # make dark brown a numerically tempting substitute for dark grey.
    neutral=(cells.max(axis=2)-cells.min(axis=2))<=3
    chromatic=np.array([c not in (0,1,11,12,15) for c in range(16)])
    distance+=neutral[:,:,None]*chromatic[None,None,:]
    bitmap=bytearray();screen=bytearray();color=bytearray();shown=np.zeros((200,320,3),dtype=np.uint8)
    for i,dist in enumerate(distance):
        if multicolor:
            # Black stays global; optimize all three per-cell colours together.
            candidates=np.column_stack((np.zeros(len(TRIPLES),dtype=int),TRIPLES))
        else:candidates=PAIRS
        errors=dist[:,candidates].min(axis=2).sum(axis=0)
        palette=candidates[int(errors.argmin())]
        codes=dist[:,palette].argmin(axis=1).reshape(8,width)
        if multicolor:
            screen.append(int((palette[1]<<4)|palette[2]));color.append(int(palette[3]))
            for row in codes:bitmap.append(sum(int(v)<<(6-2*x)for x,v in enumerate(row)))
            rendered=np.asarray(C64,dtype=np.uint8)[palette[codes]].repeat(2,axis=1)
        else:
            screen.append(int((palette[1]<<4)|palette[0]));color.append(0)
            for row in codes:bitmap.append(sum(int(v)<<(7-x)for x,v in enumerate(row)))
            rendered=np.asarray(C64,dtype=np.uint8)[palette[codes]]
        cy,cx=divmod(i,40);shown[cy*8:cy*8+8,cx*8:cx*8+8]=rendered
    return bytes(bitmap),bytes(screen),bytes(color),Image.fromarray(shown)


def mixed_story(im):
    """14 multicolour cell rows for art, then 11 hires rows for 320px text."""
    mc=convert(im,True);hi=convert(im,False)
    bitmap=mc[0][:4480]+hi[0][4480:]
    screen=mc[1][:560]+hi[1][560:]
    color=mc[2][:560]+hi[2][560:]
    shown=mc[3].copy();shown.paste(hi[3].crop((0,112,320,200)),(0,112))
    return bitmap,screen,color,shown
