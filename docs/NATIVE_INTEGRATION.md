# Native gameplay disk

The optional native bootstrap connects the recovered DOS rules to a playable
C64 keyboard/joystick interface. The original intro calls `NGSTART` when present;
otherwise the older fan engine starts. Original content stays outside the repo.

The native game includes economic simulation, research, construction,
manufacturing, armies, battles, tower capture, defence, nuclear flight,
retaliation/interception, diplomacy, computer opponents, hotseat play, victory,
defeat, progression through 28 islands, and disk save/load. Up to four factions
start with 100 colonists each. AI decisions, starting allocation, diplomacy and
campaign selection are C64 adaptations; they do not reproduce the DOS policy or
interface. Future shutdown is adapted, and special DOS shutdown branches are
not covered by the differential verifier. Human balance across all 28 islands
and real C64 disk timing remain unverified.

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
| Enter / fire | Mark army source, then select destination |
| U / H | Deploy ten idle people / demobilize army at its own tower |
| M / J | Add/remove miner on selected deposit |
| R / K | Add/remove inventor on selected design |
| C / E | Cycle category (shield, defence, attack) / design age |
| T | Cycle facility: tower, mine, laboratory, factory |
| B / V | Add/remove construction worker on selected facility |
| F / G | Add/remove factory worker; production uses an unlimited queue |
| X | Arm one researched attack unit |
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
| N | Advance after victory; restart campaign after defeat/final completion |

Start by selecting your tower. Choose attack designs with C/E and allocate
inventors with R; repeated presses allocate more. Assign miners where resources
are available. When research completes, X equips a unit. Early designs pay
resources immediately; age 4 and later designs require factory inventory.
Deploy U for additional unarmed troops, then Enter, select adjacent land and
Enter to move. Uncontested occupation constructs a tower; enemies trigger
battles. Build mines, labs and factories as technology permits. Research beyond
age 5 requires a laboratory. Install researched defences with I. Pause while
setting allocations if desired. The HUD displays ownership, people, armies,
research, resources and the current selection.

The AI allocates workers, researches designs, equips defenders and armies,
manufactures late weapons, expands, attacks, and launches available nuclear
weapons. Difficulty changes its decision interval. Truces expire after 600
simulation ticks; attacking an ally breaks the pact. Hotseat disables AI.
Movement is immediate. Ground troops require adjacent land; age 6/7/9 air
units can cross water to any land sector, leaving ground troops at the source.
This travel policy is adapted for C64. Artwork uses converted original sprites and small island
pictures with C64 character-cell colours; board layout and palette differ from
DOS. Music remains resident while effects and voices stream from disk.

## Memory and loading

| RAM | Use |
|---|---|
| `$0400–$07FF` | Screen and sprite pointers |
| `$0801–$08FF` | Standalone BASIC/ROM bootstrap |
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
| `$EF00–$FFF9` | Rare-rule overlay or streamed audio cache |

C code runs with `$01=$34`. IRQ/NMI wrappers expose I/O/KERNAL, preserve the
CPU port, and restore the interrupted mapping. Hardware and disk wrappers do
the same. Audio and rare-rule overlays invalidate one another's cache. A rare
rule returns before a sound is loaded. No x86 instructions run on the C64.

Compact sectors preserve fields used by the translated rules within the island's
legal age window (at most four ages). DOS rendering fields and out-of-window
inventories are omitted. Python and C codecs are compared for all legal windows
and all sixteen slots, including active tower construction.

`NGTABLE` has `NGR1` and 606 rule bytes. `NGCODE`/`NGRARE` use `NGC1`/`NGX1`,
a little-endian uncompressed length and RLE code. `NMAPnn` uses `NGW2`, age bounds,
sixteen terrain IDs, a compressed 96-byte picture, twelve colours and compressed
10,496-byte world. `NSPRnn` uses `NGP1` and 320 compressed sprite bytes. `NSNDnn`
uses `NGS1`, a nibble count, voice flag and compressed PCM. Every stream write
has an exact bound; truncation fails. Required content failures stop at an error
screen; audio failures disable that clip. Code files have two-byte load addresses;
stream files do not. The disk contains all 28 islands, ten sprite sets, nineteen
full clips, and the existing intro. Generated content is excluded from releases.

## Saves

F5 alternates `NSAVE0` and `NSAVE1`. Each PRG contains address `$3F80`, 128 bytes
of versioned `NGSV` metadata, and the 10,496-byte world. Metadata includes island,
players, settings, RNG, clock, alliances, truces, AI timers and sequence number.
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
for the original-executable comparisons and their limits.
