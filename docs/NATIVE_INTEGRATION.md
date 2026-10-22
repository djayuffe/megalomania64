# Native gameplay disk

The optional native bootstrap connects the recovered DOS rules to a playable
C64 keyboard/joystick interface. The original intro calls `NGSTART` when present;
otherwise the older fan engine starts. Original content stays outside the repo.

The native game includes economic simulation, research, construction,
manufacturing, armies, battles, tower capture, defence, nuclear flight,
retaliation/interception, diplomacy, computer opponents, hotseat play, victory,
defeat, campaign preparation through 28 islands, and disk save/load. A shared
100-person deployment pool starts the campaign; choose how many people to send
(default 20), an unfinished island in the current three-island epoch, and a
starting sector. Unspent people carry forward and the next epoch adds 100.
The final battle deploys one tenth of each faction's saved people. Computer
starting populations (20), AI decisions, diplomacy and interface remain C64
adaptations. Original explicit and automatic future-shutdown routines now have
DOS comparisons, including saved-population bounds and arithmetic quirks.
Human balance across all 28 islands and real C64 disk timing remain unverified.

## Frozen intro and clean handoff

The intro is complete and frozen by user request. `docs/INTRO_FROZEN.json`
records hashes of its source, timing/conversion tools, embedded artwork,
compiled entry PRG and 33 private intro/audio streams.
`python3 tools/check_intro.py --content ../recovery/content` verifies them;
the native builder also checks the frozen entry and content. The packaged fallback PRG and intro code remain unchanged.

At `NGSTART`, interrupts, sprites and SID output are stopped. The bootstrap
clears **63,232 bytes at `$0900–$FFFF`**, including RAM under I/O, BASIC and
KERNAL. It restores KERNAL IRQ/NMI vectors before loading independent gameplay
segments. Device number, hardware stack and KERNAL workspace are preserved.
Once execution has left the loader, **`$0800–$08FF` becomes gameplay code** too.
The game owns the complete 62 KiB address range `$0800–$FFFF`; screen/workspace
below it remain available to their usual hardware roles. This is an ownership
budget, not 62 KiB of free graphics space: rules, world, music and graphics share
it. No intro picture, scene decoder or credit buffer stays resident for the intro.

## Build and run

Requires the owner's version-checked DOS directory, generated recovery content,
cc65 (including its `none` library), and VICE's `c1541` disk utility. The builder
rejects output paths inside the source checkout. From the repository root:

```sh
python3 tools/build.py
python3 tools/build_native.py \
  --dos ../recovery/original/MegaLoMania_Reverse_v11/dos \
  --content ../recovery/content \
  --cc65 /private/tmp/megalomania64_cc65 \
  --out ../recovery/native \
  --disk ../recovery/MegaLoMania64_native.d81
./tools/run_vice.sh
```

The launcher prefers the local native D81, selects a 1581 drive, and enables
virtual-device turbo loading by default. `VICE_TURBO_FLOPPY=0` selects true drive
emulation. Pass an explicit D64 path to run the older fan game.
`LOAD"NGSTART",8,1` followed by `RUN` starts native gameplay directly.

## Controls

| Key | Action |
|---|---|
| WASD / port 2 joystick | Select sector |
| Enter / fire | Start prepared island; during play mark army source, then destination |
| U / H | Deploy ten idle people / demobilize army at its own tower |
| M / J | Add/remove miner on selected deposit |
| R / K | Add/remove inventor on selected design |
| C / E | Cycle category (shield, defence, attack) / design age |
| T | Cycle facility: tower, mine, laboratory, factory |
| B / V | Add/remove construction worker on selected facility |
| F / G | Add/remove factory worker; production uses an unlimited queue |
| X | Arm one researched attack unit |
| 8 | Repair selected facility using selected shield design (category 0) |
| I / O | Install/recall selected defence design at selected facility/slot |
| Z | Cycle turret slot (0–3; facility capacity still applies) |
| Q, then Enter | Mark nuclear launch source, then launch at selected target |
| L | Propose truce with selected sector's faction |
| 0 | Withdraw a tower that has reached the special future state |
| [ / ] | Select deposit |
| Space / 1,2,3 | Pause / simulation speed 1x, 3x, 9x |
| F1 | Cycle AI difficulty 1–3 |
| Y / P | Toggle hotseat / switch active human faction in hotseat |
| F5 / F7 | Save / load newest valid save |
| N | Cycle unfinished islands during preparation; continue after victory; restart after defeat/completion |
| + / - | Add/remove ten people from the proposed deployment (minimum one) |

Start in preparation: choose an island with N, choose people with +/-, select
a land sector with WASD/joystick, and press Enter. Keep people for the other
islands in the epoch. Running out of deployable people ends the campaign.
During play, start by selecting your tower. Choose attack designs with C/E and allocate
inventors with R; repeated presses allocate more. Assign miners where resources
are available. When research completes, X equips a unit. Early designs pay
resources immediately; age 4 and later designs require factory inventory.
Deploy U for additional unarmed troops, then Enter, select adjacent land and
Enter to move. Uncontested occupation constructs a tower; enemies trigger
battles. Build mines, labs and factories as technology permits. Research beyond
age 5 requires a laboratory. Install researched defences with I. Use category 0, select a shield age and
facility, then press 8 to repair; early shields cost resources and later
shields consume factory inventory. A full-health building consumes nothing. Pause while
setting allocations if desired. The HUD displays ownership, people, armies,
research, resources and the current selection.

The AI allocates workers, researches designs, equips defenders and armies,
manufactures late weapons, expands, attacks, and launches available nuclear
weapons. Difficulty changes its decision interval. Truces expire after 600
simulation ticks; attacking an ally breaks the pact. Hotseat disables AI.
Movement is immediate. Ground troops require adjacent land; age 6/7/9 air
units can cross water to any land sector, leaving ground troops at the source.
This travel policy is adapted for C64. The board uses the original 61 terrain
tiles recovered from `SMALLMAP.DAT`: executable descriptors give their 22×22
pixels, source offsets and stride. The C64 conversion retains their shapes with
black plus one foreground colour per character cell. Original army/building
sprites and island portraits remain available; layout and palette differ from DOS. Music remains resident while effects and voices stream from disk.

## Memory and loading

| RAM | Use |
|---|---|
| `$0400–$07FF` | Screen and sprite pointers |
| `$0800–$08FF` | Bootstrap initially; `NGAUX` graphics/menu helpers after handoff |
| `$0900–$0FFF` | SID/sample drivers and bounded sequential loader |
| `$1000–$26FF` | Core and world codec |
| `$2700–$2AFF` | Startup, IRQ/NMI and KERNAL wrappers |
| `$2B00–$313F` | Runtime helpers |
| `$3140–$327F` | Army/building sprites |
| `$3280–$36FF` | Input code, driver state, music tables and strings |
| `$3700–$3FFF` | Cursor sprites and charset; `$3F80` also stages save metadata |
| `$4000–$68FF` | Sixteen compact sectors, 656 bytes each |
| `$6900–$6FFF` | Drawing and stream helpers |
| `$7000–$7FFF` | Working sector, rule tables and globals |
| `$8000–$C1FF` | Native code/data |
| `$C200–$C3FF` | C software stack |
| `$C400–$D3FF` | Resident SID music |
| `$D400–$EEFF` | Combat and game orchestration code under I/O/KERNAL |
| `$EF00–$FFF9` | Rare rules, campaign overlay or streamed audio cache |

C code runs with `$01=$34`. IRQ/NMI wrappers expose I/O/KERNAL, preserve the
CPU port, and restore the interrupted mapping. Hardware and disk wrappers do
the same. Audio, rare-rule and campaign overlays invalidate one another's cache. Resident
code switches overlays only after the previous overlay has returned. Campaign
menu code touches data only; it cannot evict itself by calling a rare rule. No x86 instructions run on the C64.

Compact sectors preserve fields used by the translated rules within the island's
legal age window (at most four ages). DOS rendering fields and out-of-window
inventories are omitted. Python and C codecs are compared for all legal windows
and all sixteen slots, including active tower construction.

`NGTABLE` has `NGR2` and 706 rule bytes, including shield strengths and original repair-cap tables. `NGCODE`/`NGRARE`/`NGCAMP`/`NGAUX` use `NGC1`/`NGX1`/`NGY1`/`NGA1`,
a little-endian uncompressed length and RLE code. `NMAPnn` uses `NGW3`, age bounds, the original two-to-four-faction count,
sixteen terrain IDs, a compressed 96-byte picture, twelve colours and compressed
10,496-byte world. `NARTnn` uses `NGF1`, a compressed 2,048-byte charset,
144 board glyph codes and 144 colours. Each island needs at most 144 unique
terrain glyphs; the 164-slot game pool excludes text, portrait and save-staging
glyphs. All original terrain data stays in the private disk. `NSPRnn` uses `NGP1` and 320 compressed sprite bytes. `NSNDnn`
uses `NGS1`, a nibble count, voice flag and compressed PCM. Every stream write
has an exact bound; truncation fails. Required content failures stop at an error
screen; audio failures disable that clip. Code files have two-byte load addresses;
stream files do not. The disk contains all 28 islands, ten sprite sets, nineteen
full clips, and the existing intro. Generated content is excluded from releases.

## Saves

F5 alternates `NSAVE0` and `NSAVE1`. Each PRG contains address `$3F80`, 128 bytes
of version-2 `NGSV` metadata, and the 10,496-byte world. Metadata includes island,
players, settings, RNG, clock, alliances, truces, AI timers, completed-island bits, deployment pool/selection, preparation state
and sequence number. Older native version-1 saves are rejected.
CRC16-CCITT (seed `$FFFF`, checksum bytes treated as zero) covers all 10,624 bytes.
The completed write is verified by KERNAL. A failed write preserves the other
slot. Load probes exact length, header and CRC, chooses the newest sequence
modulo 65536, checks state ranges and falls back to the older valid slot.

Load backs up the current world and metadata beneath ROM, reads into a bounded
buffer, validates again, restores the backup on failure, then reloads banked
code and art. Audio is stopped during the backup. Disk-wait frames are excluded
from simulation time. A copy of the user's disk is always used by verification.

## Verification

```sh
python3 -m unittest discover -s tests -p 'test_native*.py' -v
python3 tools/verify_native.py \
  --disk ../recovery/MegaLoMania64_native.d81 \
  --native ../recovery/native --out ../recovery/native/check-pal \
  --model pal --handoff
```

Use `--model ntsc` for NTSC. VICE checks intro handoff, content loads, sprite and
audio bytes, deployment/movement/return, research allocation, rotating save/load,
victory/next island, code integrity and a software-stack guard. Separate tests
exercise AI defeating an idle opponent, tower destruction/capture, hotseat
elimination, diplomacy, nuclear destruction, retaliation and interception.
`--expect-load WORLD.bin` and `--expect-reject` exercise damaged save recovery.
Evidence stays in private output directories. See [rule verification](GAMEPLAY_PORT.md)
for the original-executable comparisons and their limits. `build.json` records
segment bounds, game ownership, cleared bytes and reclaimed bootstrap RAM.
