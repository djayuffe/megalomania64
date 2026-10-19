# Mega-Lo-Mania 64 — Island Wars, C64C Edition 4.0.0

**Unofficial, independently programmed, fan-inspired real-time strategy game for an unexpanded Commodore 64 / C64C.** Native NMOS 6502/6510 machine code, 64 KB RAM, VIC-II character/sprite graphics, 3-voice SID, raster-interrupt engine. Everything — assembler, build, disk-image writer, 6502 test model — is in this repository and runs with plain Python 3.

> Not a 1:1 port or licensed copy of the commercial *Mega-Lo-Mania*. It is a complete, playable strategy game of the same flavour. See [Honest status](#honest-status).

## What is in 4.0

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
| 114 automated tests on a 6502 model, mutation-checked | see below |

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
python3 tools/build.py --test              # assemble, D64, 114 tests
python3 tools/build.py --test --preview --package   # + PNG previews (needs Pillow) + release ZIP
make test
```

`tools/build.py` regenerates `src/tables.asm` (music, raster bars) and `assets/source_sprite.bin`; `--regen-gfx` rebuilds the charset (Pillow).

## Repository layout

```
src/main.asm        game rules, AI, renderer, HUD, save/load (origin $0801/$1000, data to $30F9)
src/engine.asm      v4 engine modules (origin $4000), includes:
  irq.asm           raster IRQ engine + wait_frame
  joystick.asm      port-2 decoder: moves, FIRE tap, 8 chords
  title.asm         title screen
  diplomacy.asm     truces, power calculation
  inventions.asm    era weapons, rank-up notice, extra HUD rows, source sprite
  develop.asm       U key + extra key dispatch
  tables.asm        GENERATED: music + raster-bar tables
  engine_data.asm   volatile engine state, disk blanking, get_device
assets/             charset (2 KB), cursor sprite, source-marker sprite
tools/              assembler, build, D64 writer, table/sprite generators, previews, packager
tests/              6502 model + 114 tests (engine, game rules, tools)
docs/               architecture, memory map, design, save format, QA, hardware test plan
dist/               built PRG, D64, symbols, checksums, previews, release ZIP
```

## Honest status

* **Verified here:** assembly, byte-for-byte D64 chain, reproducible builds, and 114 tests that execute the real shipped opcodes in a 6502 model with raster-IRQ firing, a KERNAL disk shim (OPEN/CLOSE/SAVE/LOAD/VERIFY/READST/SETLFS/SETNAM) and port-2 joystick pins. The suite was mutation-checked: 13 deliberate bugs (AI ignoring truces, no IRQ acknowledge, no disk scratch, raster-MSB leak, …) are all caught.
* **NOT verified (no emulator was available in the build sandbox):** anything that needs real VIC-II/SID/CIA/1541 behaviour — raster-bar jitter and looks, SID sound, joystick feel, KERNAL serial I/O against a real or emulated drive, PAL/NTSC pacing. The model shows the logic is right; it cannot show the machine agrees. Run [`docs/HARDWARE_TEST_PLAN.md`](docs/HARDWARE_TEST_PLAN.md) in VICE x64sc before trusting it, and save only to a **copy** of a disk until then.
* The raster bars are deliberately simple (not cycle-stable): expect slight edge jitter, title screen only.
* Not a 1:1 recreation: no speech, original maps, original invention tree or multiplayer.
