# Mega-Lo-Mania 64 — Campaign, Doctrine & Disk Save Edition 3.0.0

**Unofficial, independently programmed, fan-inspired real-time strategy game for an unexpanded Commodore 64 / C64C.** Native NMOS 6502/6510 machine code; 64 KB RAM; VIC-II character/sprite renderer; 3-voice SID sound. Source code, generator, image builders and 1541 disk image included.

## What is playable

- A 28-stage campaign spanning ten progressive eras. Each stage has a deterministic 12-sector island grid, distinct terrain and finite mineral deposits.
- **Four independent factions**: one human plus red, blue and gold AI rivals. Rivals can attack each other. Capture every sector to win a stage; lose every sector to be defeated. After island 28 the campaign ends in a victory screen.
- Population, mining, construction of labs and factories, technology research to rank five, weapons, defenses, and occupation/rebuilding of captured sectors.
- Two offensive orders: a standard raid and a heavy assault. Failed attacks weaken the defender and dismantle fortifications. Friendly transfers carry troops and weapons without resetting buildings.
- Toggle automated weapons production and fortification **per owned sector**.
- Three **strategic doctrines**, selectable per territory: `I` Industry (additional ore with technology 2+), `M` Military (+6 attack power at technology 2+), `D` Defense (+8 defense power at technology 2+). Technology cost increases by 8 research points each rank (`24,32,40,48,56`). Rivals assign additional workers as towns grow.
- **KERNAL-based disk save/load on device 8:** `O` saves `ML64SAVE` (using CBM DOS replace syntax), `I` reloads a versioned, length-checked and two-checksum-protected snapshot. The test interpreter models KERNAL file operations; *the real drive/VICE path has not been verified*. Use writable media with free blocks and a backup. Do not treat it as a guaranteed 1541-tested feature.
- Colour-coded island ownership, four silhouette shapes for coastlines, buildings and evolving citadels, hardware-sprite cursor, SID melody and action cues. The UI also shows names for the ten epochs.

**Important scope distinction:** This is a complete playable *independent game design* with start, strategy loop and end states, **not a 1:1 recreation or licensed copy** of the commercial *Mega-Lo-Mania*. The original game's full diplomacy, every historical invention, speech, and exact art/map data are not included. We also do not claim VICE/physical-hardware acceptance testing or that all 28 islands have been beaten in real-time human play. Disk-save routines are only model-tested, not yet verified against 1541 timing or DOS edge cases. The bundled automated tests validate the native opcodes in a software 6502 interpreter.

## Download / start

Run `dist/MegaLoMania64.prg` via VICE's autostart, a PRG loader, or mount `dist/MegaLoMania64.d64` on a Commodore 1541-compatible device. The 1541 disk directory has one PRG named `MEGALOMANIA`.

```basic
LOAD"MEGALOMANIA",8,1
RUN
```

The BASIC launcher uses `10 SYS4096`; all gameplay is machine code beginning at `$1000`.

## Keyboard controls

| Keys | Action |
|---|---|
| `W A S D` | Move selection across the non-wrapping 4 × 3 sector grid |
| `RETURN` | Set selected friendly sector as troop source |
| `X` | Launch a standard raid against an adjacent neutral/enemy sector |
| `T` | Launch a heavy assault, committing ~75% of the source population; stronger but costlier |
| `H` | Transfer half the source population (up to target capacity), plus up to four weapons, to an adjacent **friendly** sector |
| `M` / `J` | Add/remove one miner on friendly selected sector |
| `R` / `K` | Add/remove one researcher (requires local laboratory) |
| `B` | Mine upgrade, 8 ore, maximum rank 2 |
| `V` | Construct laboratory, 6 ore |
| `G` | Construct factory, 10 ore |
| `P` | Produce one weapon, 4 ore, factory required |
| `F` | Reinforce local fort, 12 ore, maximum rank 9 |
| `Y` | Toggle automatic weapon production (uses surplus ore) |
| `Q` | Cycle local doctrine `I` industry → `M` military → `D` defense → `I` |
| `Z` | Toggle automatic fortification (uses surplus ore) |
| `O` | Save current game on device 8 in file `ML64SAVE` (writable disk required) |
| `I` | Load `ML64SAVE` from device 8; validates signature, length, checksum and basic state ranges |
| `SPACE` | Pause/resume current active island |
| `C` | Continue after island victory |
| `L`, followed by `01`–`28` | Start an island checkpoint, **not** load saved live state |
| `N` | Restart campaign, or cancel checkpoint entry |

Joystick port 2: direction to move selection, FIRE on friendly sector to set source, or on other sector to make a standard raid. Heavy assaults and economic management require the keyboard. The joystick shares CIA input with keyboard scanning; physical interaction is not yet independently verified.

## Economy and interface

Sidebar displays selected sector's owner (`YOU`, `RED`, `BLUE`, `GOLD`, `FREE`), population, ore in storage, remaining ore deposit, tech, assigned miners/researchers, weapons, buildings and automated policies. `BLD:0/0/0` means mine/lab/factory; `AUTO:0/0` means auto-arm/auto-fort. The bottom of the sidebar shows the currently chosen source and the defensive level. **CPU** on the score line totals the three AI factions' holdings.

Mining yields `miners + minegrade` ore per strategy tick (subject to deposit/storage caps). Technology research costs 24, 32, 40, 48, then 56 scientist-work points (maximum rank five). Population grows once every eight ticks while enough residents are not working, and weakened colonies can recover. Each stage starts with four separated factions; every stage uses its own embedded terrain and ore patterns.

**Strategy:** Assign miners first, build a laboratory and factory on useful land, research in defended bases, and reinforce frontline colonies. Ordinary raids scout or weaken defenses, while heavy assaults break mature positions. Turn on automation selectively so weapons or fortifications do not consume all ore intended for research buildings.

## Building from source

Python 3.10+; no third-party Python packages required for normal assembly and tests:

```bash
python3 tools/build.py --test
```

The `--preview` and `--regen-gfx` switches require Pillow. The included binary art assets mean a normal build requires **no** graphics library:

```bash
python3 -m pip install Pillow
python3 tools/build.py --regen-gfx --test --preview
```

`tools/run_vice.sh` starts the compiled PRG when VICE x64sc/x64 is installed.

## Project structure

- `src/main.asm` — all machine-code rules, AI, render engine, custom HUD, audio and campaign data
- `assets/` — custom 2 KB character ROM image, 64-byte sprite, PNG glyph atlas
- `tools/asm6502.py` — original standalone two-pass assembler for supported official 6502 opcodes
- `tools/build.py` and `tools/make_d64.py` — build the PRG and verified standard 35-track 1541 image
- `tools/make_gfx.py` — regenerate character/sprite assets (optional Pillow)
- `tools/render_preview.py` — re-render **emulated screen RAM**, not real VICE screenshots
- `tests/cpu6502.py` — opcode test interpreter with deterministic KERNAL disk-save shim (not a cycle-perfect C64 emulator or actual 1541/DOS implementation)
- `tests/test_game.py` — gameplay and memory regression tests, full-stage transition probes
- `docs/` — hardware, design, QA and release notes

The included assembly source is editable; release files can be rebuilt without missing binary blobs. See `docs/HARDWARE_TEST_PLAN.md` for unverified real-machine acceptance cases, and `docs/QA_REPORT.md` for what was actually checked.

The release validation runs **43 automated tests**. No hardware/VICE test was performed.

## Save-game implementation and limitations

Press `O` to SAVE; press `I` to LOAD. Snapshot includes all 12 sector economies, territories, commanders, selected source, campaign stage, epoch and policies; geography itself is reconstructed from static island tables. Snapshot is stored in working RAM at `$C000`, then transferred using KERNAL `SETLFS`, `SETNAM`, `SAVE`/`LOAD`. Saving uses `@0:ML64SAVE` and loading uses `ML64SAVE`. Saved-file size is checked and the game rejects malformed/unsupported snapshots. The loader uses secondary address 0 to force the destination to `$C000`; it does **not** honor an untrusted PRG load address. This does not limit the maximum bytes the KERNAL loader could write if a malicious oversized file were supplied; load only game-created save files. The memory checksum is for accidental corruption, not tamper resistance.

**Drive caveat:** the Commodore DOS `@` save-with-replace command has historically had reliability issues on some 1541 firmware/media. Keep backups or use copied disk images; this function requires testing in VICE and with the user's actual storage device before trusting critical progress. The game itself loads as a regular PRG independent of SAVE support.

## What is still not a 1:1 port

Original character speech, animated production screens, specific historical invention set, diplomacy, maps and sound assets, multiplayer and original victory narrative are outside this independently created compact adaptation. Tests verify code behaviour, not visual/audio identity with the 16-bit release. This release is a functional strategy-game implementation, not a byte-exact recreation.
