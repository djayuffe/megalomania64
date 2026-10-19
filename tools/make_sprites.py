#!/usr/bin/env python3
"""Write assets/source_sprite.bin: 64-byte hires sprite (army-source diamond). No Pillow needed."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rows=[]
for y in range(21):
    bits=0
    if y<11:
        half=min(y,10-y)
        for x in range(5-half,6+half):bits|=1<<(23-x)
        if 0<y<10:  # hollow centre so the map shows through
            inner=half-1
            if inner>=0:
                for x in range(5-inner,6+inner):bits&=~(1<<(23-x))
    rows.append(bits)
data=bytearray()
for b in rows:data+=bytes(((b>>16)&255,(b>>8)&255,b&255))
data+=b'\x00'
assert len(data)==64
(ROOT/'assets/source_sprite.bin').write_bytes(bytes(data))
for b in rows[:11]:print(format(b,'024b').replace('0','.').replace('1','#'))
