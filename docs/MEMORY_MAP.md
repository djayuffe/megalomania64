# Native C64 memory plan v3

| Range | Purpose |
|---|---|
| `$0000–$00FF` | KERNAL/CPU zero page; game uses `$FB–$FE` temporary string/display pointers |
| `$0400–$07E7` | VIC-II 1000-byte screen map; sprite pointer at `$07F8` |
| `$0801–$080C` | BASIC launcher `10 SYS4096` |
| `$1000–$30FA` | Compiled game code, 28 map pairs, text, state; has no 256-byte page restrictions |
| `$3700–$373F` | Sprite 0 shape (64 bytes) |
| `$3800–$3FFF` | 2 KB custom character memory / VIC bank 0, selected with `$D018=$1E` |
| `$C000–$C0E6` | Temporary savegame file staging buffer; not used for game code |
| `$D800–$DBE7` | VIC colour RAM per character, not byte-latched program RAM |

The assembler exports symbols in `dist/symbols.txt`. Game updates only changed 6×5-character sectors and redraws HUD counters with short routines, rather than generating a 320×200 bitmap (which would need 8000 graphic bytes). Screenshots reconstructed from the native memory arrays are **not** evidence of VIC-II timing acceptance.
