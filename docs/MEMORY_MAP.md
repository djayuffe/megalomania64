# v5 development memory changes

Current exact addresses are in `dist/symbols.txt`; the v4 table below is historical.

| Range | Current role |
|---|---|
| `$0801–$080C` | BASIC autostart stub |
| `$0900–$0C3F` | SID sequencer and optional full-effect loader; build checks the boundary |
| `$0C40–$0FFF` | NMI sample player; build checks the boundary |
| `$1000–$31FF` | Main game, port campaign tables and snapshot state; exact end in symbols |
| `$3200–$333F` | Army/conquest sprites |
| `$3340–$33FF` | Music control state |
| `$3400–$347F` | Two island-card sprites |
| `$3480–$36FF` | Streaming/voice/card control state |
| `$3700–$3FFF` | Cursor/source sprites and character set |
| `$4000–$4C7F` | Original army/building source sprites |
| `$4C80–$7FFF` | Intro RAM, then first resident speech region |
| `$5400–$57E7` | Intro bank-1 colour shadow, before speech takes over |
| `$8000–$BFFF` | Engine and 9000-byte main effect bank; exact end below `$C000` |
| `$C000–$C3E7` | Intro bank-3 colour shadow; save buffer used after intro exit |
| `$C400–$D3FF` | Optional SID score: title bank first, larger game bank after intro |
| `$CC00–$CFE7` | Intro bank-3 screen, before the game score takes over |
| `$D400–$DFFF` (RAM) | Second full-effect region, distinct from the SID/I/O registers |
| `$E000–$FF3F` | Intro bank-3 bitmap |
| `$E000–$FFF9` | Second resident speech region after title exit |
| `$FFFA/$FFFB` (RAM) | NMI vector for briefly banking ROM/I/O out |

The loader disables IRQs only around individual writes beneath I/O and restores
`$01` and the IRQ flag. NMI is stopped before disk access. The IRQ score reader
uses RAM beneath I/O only while no sample NMI is active. Sample fetches briefly
map ROM/I/O out and restore the CPU port before returning.

Effects cross from `smp_end` to `$D400`; speech crosses `$8000` to `$E000`.
Both bounds are independent, and full effects do not overlap the game score.
Original effects run at approximately 5 kHz (PAL latch 196 / NTSC 203), speech
at approximately 4 kHz (PAL 245 / NTSC 254). SID oscillator 3 supplies a DC pulse
during digis on 6581; all three oscillators do so on detected 8580 hardware.
The sequencer restores complete musical oscillator state afterward.

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
