"""Original SMALLMAP descriptors and bounded C64 character conversion."""
import struct
from orig_convert import C64
from orig_import import _chunks
from lzhuf import decompress

GLYPHS=list(range(32))+list(range(96,128))+list(range(140,240))
def resource(path):
    data=path.read_bytes()
    return data if data.startswith(b'FORM') else decompress(data)

def terrain_tiles(exe,raw):
    # CS0:D8BF subtracts one from the map tile ID, multiplies by 16, and
    # indexes DS:CD18. Each descriptor names SMALLMAP and its mask buffers.
    if exe[0x1600+0xd8bf:0x1600+0xd8c4]!=bytes.fromhex('832ef09901'):
        raise ValueError('terrain descriptor instruction mismatch')
    if len(raw)!=24640:raise ValueError('invalid SMALLMAP size')
    result=[]
    for index in range(61):
        segment,offset,mask,mask_offset,w,h,pitch,mask_pitch=struct.unpack_from('<8H',exe,0x22f00+0xcd18+index*16)
        if (segment,mask,w,h,pitch,mask_pitch)!=(0xafa8,0xafaa,22,22,160,40):
            raise ValueError('unsupported terrain descriptor')
        result.append(planar_tile(raw,offset,w,h,pitch))
    return result

def planar_tile(raw,offset,w,h,pitch):
    if w<=0 or h<=0 or pitch<((w+15)//16)*8 or offset<0 or offset+(h-1)*pitch+((w+15)//16)*8>len(raw):
        raise ValueError('terrain outside resource')
    rows=[]
    for y in range(h):
        row=[]
        for x in range(w):
            at=offset+y*pitch+(x//16)*8
            row.append(sum(((int.from_bytes(raw[at+p*2:at+p*2+2],'big')>>(15-x%16))&1)<<p for p in range(4)))
        rows.append(row)
    return rows

def palette(path):
    for kind,data in _chunks(resource(path)):
        if kind==b'CMAP':return [tuple(data[i:i+3])for i in range(0,len(data),3)]
    raise ValueError('missing original map palette')

def convert(tiles,terrain,colors,font,portrait):
    if len(terrain)!=16 or len(font)!=2048 or len(portrait)!=96:raise ValueError('invalid graphics input')
    font=bytearray(font);font[1024:1120]=portrait
    lookup={};maps=bytearray();inks=bytearray()
    for tile in terrain:
        if not 0<=tile<=len(tiles):raise ValueError('invalid terrain ID')
        pixels=tiles[tile-1]if tile else [[0]*22 for _ in range(22)]
        for cy in range(3):
            for cx in range(3):
                cell=[]
                for y in range(8):
                    for x in range(8):
                        sx=cx*8+x-1;sy=cy*8+y-1
                        cell.append(colors[pixels[sy][sx]]if 0<=sx<22 and 0<=sy<22 else (0,0,0))
                distances=[[sum((rgb[k]-c[k])**2 for k in range(3))for c in C64]for rgb in cell]
                ink=min(range(1,16),key=lambda c:sum(min(d[0],d[c])for d in distances))
                glyph=bytes(sum((distances[y*8+x][ink]<distances[y*8+x][0])<<(7-x)for x in range(8))for y in range(8))
                if glyph not in lookup:
                    if len(lookup)>=len(GLYPHS):raise ValueError('terrain exceeds game glyph budget')
                    code=GLYPHS[len(lookup)];lookup[glyph]=code;font[code*8:code*8+8]=glyph
                maps.append(lookup[glyph]);inks.append(ink)
    return bytes(font),bytes(maps),bytes(inks),len(lookup)
