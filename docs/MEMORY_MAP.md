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
| `$4000–$4C7F` | VIC bank 1: `orig_army` (10 epochs × 4 frames × 64 bytes, pointers 0–39) and `orig_build` (10 icons, pointers 40–49), original-art multicolour sprites. The intro shows them directly (parade); the game copies the current epoch into bank 0 |
| `$4D00–$50E7` | `intro_screen_src`: screen-RAM colours of the intro picture; the intro reveals it row by row into `$5C00` |
| `$5800–$5BE7` | Intro picture colour data (revealed row by row into colour RAM) |
| `$5C00–$5FE7` | Intro picture screen RAM (VIC bank 1, starts black); `$5FF8–$5FFF` intro sprite pointers |
| `$6000–$7F3F` | Intro picture multicolour bitmap, 8000 bytes (VIC bank 1) |
| `$8000–$9446` | **Engine**: IRQ, joystick, title/intro, sound, sample player, fx, hud, diplomacy, inventions, develop, original-art code, tables, engine state (`dist/symbols.txt` has exact addresses). Not in the save snapshot |
| `$9447–$B517` | `smp_data`: the 11 original Amiga effects as packed 4-bit samples (5 kHz), 8401 bytes. `$A000–$BFFF` is RAM because `irq_install` banks BASIC out (`$01 = $36`) |
| `$B518–$BFFF` | Free (≈2.7 KB) |
| `$C000–…` | Save/load staging buffer (8 + N bytes) |
| `$D800–$DBE7` | Colour RAM. **Text must use colours 0–7**: values 8–15 select multicolour glyphs |

VIC bank 0 is `$0000–$3FFF` (the game). The intro lives in VIC bank 1 (`$4000–$7FFF`, `$DD00` low bits `%10`, `$D018=$78`: screen `$5C00`, bitmap `$6000`); `title_screen` switches to it and back and saves/restores the game's sprite registers around it. The engine code (`$8000–`) is outside both banks. `tools/build.py` fails the build if code/state reaches `$3200` or the PRG reaches `$C000`.

Sample player: CIA 2 timer A raises an NMI at ≈5 kHz (latch 196 PAL / 203 NTSC); `nmi_entry` (vector `$0318`) steps `sample_step`, which writes one 4-bit sample to the SID volume (`$D418`). The raster IRQ, the SID voices and the sequencer are muted/paused while a sample plays. `disk_begin` stops it (the serial bus is timing-critical).
