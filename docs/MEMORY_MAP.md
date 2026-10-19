# Native C64 memory plan v4

| Range | Purpose |
|---|---|
| `$0000–$00FF` | Zero page. Game uses `$FB–$FE` (text/screen pointers). Touches KERNAL `$9D` (message flag, set 0), `$BA` (device, read), `$C6` (key queue length, cleared), `$CC` (cursor blink, set 1) |
| `$0314/$0315` | IRQ vector → `irq_handler` |
| `$0400–$07E7` | Screen; `$07F8` cursor sprite pointer (`$DC`), `$07F9` source-marker pointer (`$DD`) |
| `$0801–$080C` | BASIC `10 SYS4096` |
| `$1000–$30F9` | Game code, 28 maps, text, state (snapshot block `owner..cpu_count`) |
| `$3700–$373F` | Sprite 0 (cursor) |
| `$3740–$377F` | Sprite 1 (army-source diamond) |
| `$3800–$3FFF` | 2 KB character set (VIC bank 0, `$D018=$1E`) |
| `$4000–$491F` | **v4 engine**: IRQ, joystick, title, diplomacy, inventions, develop, tables, engine state (`dist/symbols.txt` has exact addresses) |
| `$4920–$BFFF` | Free (≈30 KB) |
| `$C000–…` | Save/load staging buffer (8 + N bytes) |
| `$D800–$DBE7` | Colour RAM. **Text must use colours 0–7**: values 8–15 select multicolour glyphs |

VIC bank 0 is `$0000–$3FFF`; the engine sits above it because it needs no VIC access. `tools/build.py` fails the build if code/state reaches `$3700` or the PRG reaches `$C000`.
