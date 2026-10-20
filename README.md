Audio/colour update (20 October 2026): the local full disk now retains all four
MOD parts in a SID arrangement, follows volume slides, plays full-length original
effects and queues speech after them. Original story pictures use multicolour
art with hires lettering; greys remain neutral. The `MUSICG` and `EFFECTS` files
are generated alongside the other local content. See
[reconstruction details](docs/REVERSE_ENGINEERING_V5.md).

# v5 reconstruction in progress

The lost cloud working copy has been rebuilt locally from v4.4. The DOS LZHUF
resources now decode, and an optional full disk streams 20 original picture scenes,
loads eight resident voices, plays two recovered MOD scores as three-voice SID
arrangements, and reads an original island tile for each level.
These are new local implementations, not recovered copies of the missing v5 source.
See [the evidence and build instructions](docs/REVERSE_ENGINEERING_V5.md).

The Amiga disk's 510-byte payload / two-byte footer layout now recovers 21 images,
20 sounds and the original `war14` / `choose3` music modules. The SID arrangements
approximate their sample timbres and omit one Amiga channel.

The original game's rules, maps, and exact intro motion and timing have not been
fully reconstructed. Credit framing, scene durations, voice selection and atlas
ordering are port choices. The existing strategy engine remains this port's own.
This development build is not a verified release.

# Mega-Lo-Mania 64 — Island Wars, C64C Edition 4.4.0

**Unofficial, independently programmed, fan-inspired real-time strategy game for an unexpanded Commodore 64 / C64C.** Native NMOS 6502/6510 machine code, 64 KB RAM, VIC-II character/sprite graphics, 3-voice SID, raster-interrupt engine. Everything — assembler, build, disk-image writer, 6502 test model — is in this repository and runs with plain Python 3.

> Not a 1:1 port or licensed copy of the commercial *Mega-Lo-Mania*. It is a complete, playable strategy game of the same flavour. See [Honest status](#honest-status).

## What is new in 4.4 — original sound effects and a new multi-scene intro

| Area | Status |
|---|---|
| **Original Amiga sound effects**: 11 8SVX samples (stick, throw, musket, machine gun, cannon, missile, laser, explosion, grunt, orchestra hit, timpani) down-converted to 4 bit / 5 kHz and played through the SID master volume by a CIA 2 NMI player; attacks use the weapon of the current epoch, capture = explosion, sector lost = grunt, victory = orchestra hit, defeat = timpani. The SID voices are muted and the music waits while a sample plays | **new** |
| **Intro**: (1) the galaxy opens row by row from the middle with the original orchestra hit; (2) eight original soldiers (epochs 0–7 from `ARMIES.LBM`) march in from the left, each arrival playing that epoch's weapon sample; (3) raster bars behind the logo, title tune, PRESS FIRE. Any key/FIRE skips it and restores the game's sprite registers | **new** |
| Memory: engine moved to `$8000`, 8.4 KB sample bank to `$B517` (`$A000–$BFFF` is RAM with BASIC banked out) | changed |
| Bugs found before release: the self-modifying sample read was assembled as a zero-page `LDA` and overwrote its own code (model test); the colour pulse and army-sprite code ran during the intro and hijacked the soldier sprites (model test) | fixed |
| 177 tests, 45 mutants (the 6502 model now supports RTI) | updated |

**The original Amiga intro is not ported.** Its picture data in the Amiga disk carves is fragmented and the DOS `.DAT` files are undecoded, so no original intro sequence could be recovered; the intro above is a new sequence made from the decoded original art and sounds. The Amiga music score is not available either (the tunes stay this port's own). See [`docs/ORIGINAL_DATA.md`](docs/ORIGINAL_DATA.md).

## What was new in 4.3 — original game data, down-converted

The original 1991 data files (PC *Mega-Lo-Mania*, from the reverse-engineering package v11) were unpacked and converted for the C64. See [`docs/ORIGINAL_DATA.md`](docs/ORIGINAL_DATA.md) for exactly what was used, what could not be, and the licence note.

| Area | Status |
|---|---|
| **Intro picture = the original galaxy** (`MTARFLD.LBM`, 320x256, 16 colours) re-sampled to a 160x200 C64 multicolour bitmap (black / blue / light blue / cyan / white ramp, ordered dither, per-cell 3-colour constraint) under the logo | **new** |
| **Marching army**: attacks now send the original-art soldier (`ARMIES.LBM` walk frames, one strip per epoch, 4-frame cycle, 2x2 expanded multicolour sprite 2) from the source to the target sector in 32 frames, in the attacker's colour | **new** |
| **Conquest icon**: a captured sector shows an original-art building (`BUILDS.LBM`, multicolour sprite 3) in the new owner's colour once the army arrives, then blinks out | **new** |
| **Original island names** (`MEGA.EXE`): ALOHA, BAZOOKA, CILLA … ZAPPA, then MEGALOMANIA and THE MOTHER, shown on the HUD instead of the generic title | **new** |
| `tools/orig_import.py` (ILBM reader + EXE text tables) and `tools/orig_convert.py --orig <dir>`; the original files are **not** in this repository | **new** |
| 149 tests (14 new), 23 mutants | updated |

Not recovered by anyone yet (so **not** used): the 54 proprietary `.DAT` files — original maps, tech tree, balance numbers, speech and music. Gameplay is still this port's own.

## What was new in 4.2

| Area | Status |
|---|---|
| **Intro picture**: full-screen 160x200 multicolour bitmap (sunset, volcano, castle, ships, gold logo) in VIC bank 1 with the raster bars running behind the logo and a colour-cycling PRESS FIRE | **new** |
| **Sound effects** (13, table-driven with priority and pitch sweeps): select, error, attack, capture, sector lost, invention, truce, build, disk, cursor tick, repulsed, victory, defeat | **new** |
| **Music**: pulse lead with PWM + sawtooth bass, notes re-gated per step; new **victory** and **defeat** tunes | **new** |
| **Effects**: border flashes (capture, loss, invention, win), screen shake on assault, pulsing cursor and source-marker colours, a different frame colour per epoch | **new** |
| **HUD colour**: faction-coloured owner row, coloured score line, sidebar and help rows (hires colours only) | **new** |
| Bug found by the new tests: `set_border` clobbered Y inside `load_island` (every island got the same terrain) | fixed before release |
| Bug found in VICE: HUD colours 8-15 turned glyphs into multicolour garbage | fixed before release |

## What was new in 4.1

First release checked in a **real emulator** (VICE 3.7.1 x64sc) as well as in the 6502 model.

| Area | Status |
|---|---|
| **Title screen layout**: the raster bars sat on top of the subtitle lines in VICE and washed them out; bars now run in their own band above the text, which moved down | fixed (found in VICE) |
| **Game speed keys `1` `2` `3`** (slow / normal / fast, shown top-right as `SPEED n`); default is now *normal* (0.48 s per tick, was 0.32 s) | **new** |
| **AI pacing**: one AI move per 16 ticks (8 from epoch 5; was 8 / 4) and the AI only assaults with a 25 % margin over the defender; a competent player can now survive and win | **balance** |
| `tools/vice_smoke.sh`: headless VICE boot + screenshots on PAL and NTSC (`dist/vice/*.png`) | **new** |

## What was in 4.0

| Area | Status |
|---|---|
| 28 islands, 10 epochs, 12 sectors per island, finite ore deposits | done (3.0) |
| 4 factions (you + red/blue/gold AI), AI-vs-AI wars, sieges, heavy assaults, troop transfers | done (3.0) |
| Mines, labs, factories, research to rank 5, weapons, forts, doctrines (I/M/D), automation | done (3.0) |
| **Raster-IRQ engine**: one IRQ per frame (CIA timer IRQ off) chains into the KERNAL; vblank-driven, drift-free tick clock; SID music + SFX run from the IRQ | **new** |
| **Title screen** with colour-cycled logo and a chained-IRQ raster-bar stack | **new** |
| **Diplomacy**: propose truces (`E`); rivals accept if you are at least as strong; AI honours them; attacking a partner voids the pact | **new** |
| **Inventions**: each epoch has a signature weapon on the HUD; every research rank-up announces `INVENTION: MUSKET MARK 3` | **new** |
| **`U` develop**: spends the sector's ore on the next most useful step (lab → factory → miners → mine → scientists → fort → arms …) | **new** |
| **Full joystick play**: FIRE tap + 8 FIRE+direction chords reach every command that matters, plus context-sensitive FIRE on pause/victory/defeat screens | **new** |
| Army-source marker (hardware sprite 1) | **new** |
| Four SID tunes (ancient / medieval / industrial / title), chosen by epoch | **new** |
| **Safer disk save**: DOS `S0:` scratch + plain `SAVE`, then a KERNAL **VERIFY** read-back and status check; device follows the drive you booted from; screen and sprites blanked around serial I/O; snapshot v4 (includes truces) | **new** |
| Fixes: KERNAL cursor blink could XOR screen RAM; KERNAL "SAVING/SEARCHING" messages suppressed; stale keystrokes flushed at title | **new** |
| 135 automated tests on a 6502 model, mutation-checked | see below |

## Run it

Autostart `dist/MegaLoMania64.prg` in VICE (x64sc), or mount `dist/MegaLoMania64.d64` on a 1541/SD2IEC/Ultimate:

```basic
LOAD"MEGALOMANIA",8,1
RUN
```

`10 SYS4096` starts the machine-code game at `$1000`. Press **FIRE or any key** on the title screen.

## Controls

### Keyboard

| Keys | Action |
|---|---|
| `W A S D` | Move the selection over the 4 × 3 island grid (no wrap) |
| `RETURN` | Make the selected own sector the army source (sprite 1 marks it) |
| `X` / `T` | Raid / heavy assault against an adjacent non-own sector |
| `H` | Send half the source garrison + up to 4 weapons to an adjacent own sector |
| `M` `J` / `R` `K` | Add / remove one miner / one scientist |
| `B` `V` `G` `P` `F` | Mine upgrade (8 ore) · laboratory (6) · factory (10) · weapon (4) · fort (12) |
| `Y` / `Z` | Toggle auto-arms / auto-fort for the selected sector |
| `Q` | Cycle doctrine: **I**ndustry → **M**ilitary → **D**efense |
| **`E`** | **Propose a truce to the owner of the selected rival sector** |
| **`U`** | **Develop the selected own sector (smart build)** |
| `O` / `I` | Save / load `ML64SAVE` on the boot device (default 8) |
| `L` + `01`–`28` | Start an island checkpoint (not a live-state load) |
| `SPACE` | Pause |
| `1` `2` `3` | Game speed: slow / normal / fast |
| `C` / `N` | Next island after a win / new campaign |

### Joystick (port 2)

| Input | Action |
|---|---|
| Stick | Move selection (one step per newly pressed direction) |
| FIRE tap | `RETURN` on own land, raid otherwise · resume when paused · next island on the win screen · new campaign on defeat |
| FIRE held + stick **up** | `T` heavy assault |
| FIRE + **down** | `U` develop |
| FIRE + **left** | `Q` doctrine |
| FIRE + **right** | `E` truce |
| FIRE + up-left / up-right | `H` send troops / `Y` auto-arms |
| FIRE + down-left / down-right | `Z` auto-fort / pause |

A chord fires after the pattern is stable for 4 frames; moving the stick with FIRE held cancels the FIRE tap.

## HUD

Sidebar rows: sector number, owner, **PACT** (truce ticks left with the selected rival, `--` otherwise), people, ore, deposit, **ARM** (this era's weapon), tech, era name, miners, role, labs, auto flags, weapons, buildings (`mine/lab/factory`), base and fort. Score line: your land, CPU land, tick, era and island.

## Diplomacy rules

* Strength = Σ over a faction's sectors of `people + weapons/2 + 4·tech`.
* A rival accepts when **your strength ≥ theirs**, otherwise it refuses and will not talk for 60 ticks.
* A truce lasts 90 ticks. While it holds, that rival never attacks your sectors (other rivals still may).
* Launching a real attack (garrison ≥ 8) on a truce partner voids the pact and starts a 60-tick cool-down. Attacking free land never does.
* When a truce expires a 60-tick cool-down starts, so truces cannot be chained indefinitely.

## Build

Python 3.10+, no third-party packages for assembling and testing:

```bash
python3 tools/build.py --test              # assemble, D64, 177 tests
python3 tools/build.py --test --preview --package   # + PNG previews (needs Pillow) + release ZIP
make test
```

`tools/build.py` regenerates `src/tables.asm` (music, raster bars) and `assets/source_sprite.bin`; `--regen-gfx` rebuilds the charset (Pillow).

## Repository layout

```
src/main.asm        game rules, AI, renderer, HUD, save/load (origin $0801/$1000, data to $30F9)
src/engine.asm      engine modules (origin $8000; bank-1 art at $4000), includes:
  irq.asm           raster IRQ engine + wait_frame
  joystick.asm      port-2 decoder: moves, FIRE tap, 8 chords
  title.asm         intro: reveal, soldier parade, title
  sample.asm        NMI 4-bit sample player (original Amiga effects)
  orig.asm          original-art army/icon sprites, island names
  diplomacy.asm     truces, power calculation
  inventions.asm    era weapons, rank-up notice, extra HUD rows, source sprite
  develop.asm       U key + extra key dispatch
  tables.asm        GENERATED: music + raster-bar tables
  engine_data.asm   volatile engine state, disk blanking, get_device
assets/             charset (2 KB), cursor sprite, source-marker sprite, intro picture, orig/ (down-converted original sprites, galaxy, 4-bit samples)
tools/              assembler, build, D64 writer, table/sprite generators, previews, packager
tests/              6502 model + 135 tests (engine, game rules, tools)
docs/               architecture, memory map, design, save format, QA, hardware test plan
dist/               built PRG, D64, symbols, checksums, previews, release ZIP
```

## Honest status

* **Verified here:** assembly, byte-for-byte D64 chain, reproducible builds, and 149 tests that execute the real shipped opcodes in a 6502 model with raster-IRQ firing, a KERNAL disk shim (OPEN/CLOSE/SAVE/LOAD/VERIFY/READST/SETLFS/SETNAM) and port-2 joystick pins. The suite was mutation-checked: 23 deliberate bugs (AI ignoring truces, no IRQ acknowledge, no disk scratch, raster-MSB leak, …) are all caught.
* **Verified in VICE 3.7.1 x64sc (headless, PAL and NTSC):** the D64 autostarts; title screen with raster bars and colour cycling renders (screenshots in `dist/vice/`); the map, HUD, cursor and army-source sprites render; keyboard input (move, base, assault, build, speed keys, new game) works; an assault captures territory; `O` writes `ML64SAVE` to the D64 (one block, read back with `c1541`) and `I` restores it. Disk access used VICE's *virtual device* (KERNAL traps), **not** hardware-level 1541 emulation.
* **Sound checked in VICE by recording:** the title tune's notes (98, 392 and 587 Hz = G2, G4, D5) show up in a WAV captured from VICE's SID. Nobody has listened to the SFX or judged the mix.
* **NOT verified:** the sound effects' loudness/feel, real joystick feel (the joystick path is only model-tested), hardware-level 1541 / SD2IEC / Ultimate serial timing, a real C64C, raster-bar stability on real silicon, and balance against a human player over all 28 islands. Run [`docs/HARDWARE_TEST_PLAN.md`](docs/HARDWARE_TEST_PLAN.md) on real hardware and save only to a **copy** of a disk until then.
* The raster bars are deliberately simple (not cycle-stable): expect slight edge jitter, title screen only.
* Not a 1:1 recreation: the original *graphics* and island names are used (down-converted), but there are no original maps, invention tree, speech or multiplayer — the proprietary `.DAT` files are undecoded. The sheet-row-to-epoch assignment of the soldier and building sprites is this port's choice.
* New in 4.4: the sample player and the intro run in VICE (PAL; screenshots, a WAV recording showing sample bursts then the title tune, and a memory read showing a full explosion sample played and stopped), but **nobody has listened** to the samples or judged their 4-bit / 5 kHz quality, NTSC was not run for 4.4, and the NMI load (about 5 kHz) makes raster-bar edges jitter during samples. Not tried on real hardware.
* New in 4.3 and only checked in VICE by screenshot: the marching army and conquest icon (real-time positions, colours). Not judged on real hardware.
