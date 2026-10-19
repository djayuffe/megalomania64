#!/usr/bin/env python3
"""Build original VIC-II custom character ROM (2 KB) and sprite (64 bytes)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
DIR=Path(__file__).resolve().parents[1]/'assets';DIR.mkdir(exist_ok=True)
chars=bytearray(2048)
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
font=ImageFont.truetype(fontpath,9) if Path(fontpath).exists() else ImageFont.load_default()
for ascii_code in range(33,127):
 ch=chr(ascii_code)
 im=Image.new('1',(8,8));d=ImageDraw.Draw(im)
 box=d.textbbox((0,0),ch,font=font)
 x=(8-(box[2]-box[0]))//2-box[0]
 y=(8-(box[3]-box[1]))//2-box[1]
 d.text((x,y),ch,font=font,fill=1)
 for row in range(8):
  b=0
  for col in range(8):b|=(1 if im.getpixel((col,row)) else 0)<<(7-col)
  chars[ascii_code*8+row]=b
# Tiles use two-bit multicolor pixels: 00 background blue, 01 green, 10 lightgreen, 11 sector colour.
def tile(c,rows):
 assert len(rows)==8
 for y,row in enumerate(rows):
  assert len(row)==4 and all(ch in '0123' for ch in row)
  chars[c*8+y]=sum(int(ch)<<(6-2*x) for x,ch in enumerate(row))
tile(1,['1111','1211','1111','1131','1111','2111','1111','1111']) # prairie
tile(2,['1111','1311','3331','1331','1111','1131','1333','1111']) # forest
tile(3,['0000','0020','0220','2222','2232','2322','2222','1111']) # highland
tile(4,['0000','0000','0010','0111','1111','1111','1101','1111']) # coast
tile(5,['0000','0010','0000','1000','0000','0001','0000','0100']) # dry
tile(6,['0000','0003','0000','0000','0300','0000','0003','0000']) # deep ocean + sparse foam
tile(9,['0000','0330','3333','3233','3333','3133','3333','1111']) # HQ
tile(10,['0000','0030','0030','0333','0030','0300','3000','0000']) # infantry
tile(11,['0300','0330','0333','0300','0300','3330','3330','1111']) # flag
tile(12,['1111','1311','1111','2111','1111','1113','1121','1111']) # flowered meadow
tile(13,['1111','3131','3333','1311','1111','3311','3331','1311']) # clustered forest
tile(14,['0000','0200','2220','2232','2322','2222','2222','1111']) # rugged ridge
tile(15,['0000','0001','0010','0111','1111','1110','1011','1111']) # broken coastline
tile(16,['0000','0000','0100','0000','1100','1110','1000','1111']) # shaded dunes
# Epoch-specific silhouettes: stone keep, feudal fort, industrial mill,
# radio tower, modern megastructure. Uses one VIC-II charset across all eras.
tile(17,['0000','0030','0333','3333','3233','3333','3333','1111'])
tile(18,['3030','3333','3333','3233','3333','3333','3333','1111'])
tile(19,['0003','0033','0333','3333','3233','3333','3333','1111'])
tile(20,['0030','0030','3333','3333','3233','3333','3333','1111'])
tile(21,['0330','3333','0330','3333','3233','3333','3333','1111'])
tile(22,['0010','0131','1331','3333','3131','1111','1111','1111']) # mine

tile(23,['0330','0330','3333','3133','3313','3333','1111','1111']) # lab
tile(24,['0303','0303','3333','3233','3333','3133','1111','1111']) # factory
# 24x21 outline targeting sprite, raster shapes.
sprite=bytearray(64)
for y in range(21):
 pixels=[0]*24
 if y in (0,1,19,20):
  for x in list(range(0,7))+list(range(17,24)):pixels[x]=1
 else:
  for x in (0,1,22,23):pixels[x]=1
  if y in (9,10,11):pixels[11]=1;pixels[12]=1
 for i in range(3):sprite[y*3+i]=sum(pixels[8*i+j]<<(7-j) for j in range(8))
(DIR/'charset.bin').write_bytes(chars)
(DIR/'cursor_sprite.bin').write_bytes(sprite)
# Tile atlas for development documentation, not C64 framebuffer asset.
scale=4;atlas=Image.new('RGB',(16*8*scale,16*8*scale),(15,18,37))
colors=['#17427b','#398a41','#9cce78','#ffe6a7']
for glyph in range(256):
 for yy in range(8):
  data=chars[glyph*8+yy]
  if glyph in (1,2,3,4,5,6,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24):
   for xx in range(4):
    color=colors[(data>>(6-2*xx))&3]
    ImageDraw.Draw(atlas).rectangle(((glyph%16*8+xx*2)*scale,(glyph//16*8+yy)*scale,((glyph%16*8+xx*2+2)*scale-1),((glyph//16*8+yy+1)*scale-1)),fill=color)
  else:
   for xx in range(8):
    if data&(1<<(7-xx)):
     ImageDraw.Draw(atlas).rectangle(((glyph%16*8+xx)*scale,(glyph//16*8+yy)*scale,((glyph%16*8+xx+1)*scale-1),((glyph//16*8+yy+1)*scale-1)),fill='#f5eee3')
atlas.save(DIR/'charset_atlas.png')
print('Generated custom VIC-II charset and targeting sprite')
