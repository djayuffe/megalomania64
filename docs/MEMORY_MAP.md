# Native C64 memory plan v4

| Range | Purpose |
|---|---|
| `$0000–$00FF` | Zero page. Game uses `$FB–$FE` (text/screen pointers). Touches KERNAL `$9D` (message flag, set 0), `$BA` (device, read), `$C6` (key queue length, cleared), `$CC` (cursor blink, set 1) |
| `$0314/$0315` | IRQ vector → `irq_handler` |
| `$0400–$07E7` | Screen; `$07F8` cursor sprite pointer (`$DC`), `$07F9` source-marker pointer (`$DD`) |
| `$0801–$080C` | BASIC `10 SYS4096` |
| `$1000–$30F9` | Game code, 28 maps, text, state (snapshot block `owner..cpu_count`) |
| `$3200–$32FF` | Sprites 2 frames 0–3: marching army, current epoch's walk cycle (pointers `$C8–$CB`), copied from `orig_army` |
| `$3300–$333F` | Sprite 3: conquest building icon (pointer `$CC`), copied from `orig_build` |
| `$3700–$373F` | Sprite 0 (cursor) |
| `$3740–$377F` | Sprite 1 (army-source diamond) |
| `$3800–$3FFF` | 2 KB character set (VIC bank 0, `$D018=$1E`) |
| `$4000–$48D1` | **Engine**: IRQ, joystick, title, sound, fx, hud, diplomacy, inventions, develop, tables, engine state (`dist/symbols.txt` has exact addresses). `engine_end` must stay below `$5800` (build-checked) |
| `$5800–$5BE7` | Intro picture colour data (copied to colour RAM) |
| `$5C00–$5FE7` | Intro picture screen RAM (VIC bank 1) |
| `$6000–$7F3F` | Intro picture multicolour bitmap, 8000 bytes (VIC bank 1) |
| `$7F40–$893F` | `orig_army`: 10 epochs × 4 frames × 64 bytes (original-art multicolour sprites) |
| `$8940–$8BBF` | `orig_build`: 10 building icons × 64 bytes |
| `$8BC0–$BFFF` | Free (≈13 KB) |
| `$C000–…` | Save/load staging buffer (8 + N bytes) |
| `$D800–$DBE7` | Colour RAM. **Text must use colours 0–7**: values 8–15 select multicolour glyphs |

VIC bank 0 is `$0000–$3FFF` (the game). The intro picture lives in VIC bank 1 (`$4000–$7FFF`, `$DD00` low bits `%10`, `$D018=$78`: screen `$5C00`, bitmap `$6000`); `title_screen` switches to it and back. The engine code sits in the same bank but the VIC never fetches it. `tools/build.py` fails the build if code/state reaches `$3200` or the PRG reaches `$C000`.
