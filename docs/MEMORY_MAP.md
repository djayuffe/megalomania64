# v5 development memory changes

The v4 table below is retained as historical context. Current addresses come from
`dist/symbols.txt`; `tools/build.py` enforces the `$3200` and `$C000` boundaries.

| Range | Current role |
|---|---|
| `$1000–$31B0` | Main logic, port campaign tables, snapshot state |
| `$3200–$333F` | Existing army and conquest sprites |
| `$3340–$336C` | Music control state, outside army/card sprite RAM |
| `$3480–$3558` | Streaming control data; exact end in symbols, checked below `$3700` |
| `$3400–$347F` | Two island-card sprites, loaded per island |
| `$3700–$3FFF` | Cursor/source sprites and character set |
| `$4000–$4C7F` | Original army/building source sprites, retained throughout play |
| `$4C80–$7FFF` | Intro screen/bitmap initially; first 13184-byte voice region after title exit |
| `$8000–$BF27` | Engine modules, streaming/voice/card routines, volatile state, original effect samples; exact end in symbols |
| `$C000–…` | Existing save/load staging buffer |
| `$C400–$C7E7` | Intro bank-1 colour shadow; reused by original-score bank after intro |
| `$C800–$CBE7` | Intro bank-3 colour shadow |
| `$CC00–$CFE7` | Intro bank-3 screen; sprite pointers excluded from writes |
| `$E000–$FF3F` | Intro bank-3 bitmap |
| `$E000–$FFF9` | Second 8186-byte voice region after title exit |
| `$FFFA/$FFFB` (RAM) | NMI vector for the brief KERNAL-out sample fetch; installed before disk streaming |

Intro bank 1: bitmap `$6000`, screen `$5C00`, `$D018=$78`. Intro bank 3:
bitmap `$E000`, screen `$CC00`, `$D018=$38`. Engine code stays outside both.
The `TITLE` disk file restores the embedded bitmap before the native title runs.
The optional 1888-byte `MUSIC` bank then reuses `$C400–$CB5F` for PAL/NTSC
frequency tables and two bounded three-SID-voice event streams.
Speech then reuses intro RAM; subsequent island cards use `$3400` and preserve it.

The NMI voice player wraps the read cursor from `$8000` to `$E000`. Its file index
must describe eight nonempty, even-nibble, contiguous clips, with the final byte
below `$FFFA`. KERNAL is mapped out only around the sample read and the previous
CPU-port value is restored. Weapon effects still use the unchanged 5 kHz bank;
original speech uses approximately 4 kHz (PAL latch 245 / NTSC 254).

## Historical v4 layout

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
