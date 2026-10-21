# Native integration development disk

The optional native bootstrap connects the separately verified DOS rules to a
C64 front end. The existing intro calls `NGSTART` if present; otherwise the fan
engine starts. The native bootstrap replaces the old game code, resets the
hardware stack, loads six address-tagged code/support files, installs its own
raster IRQ, and starts the C front end. Original content stays outside the repo.

This is an integration build, **not a complete game port**. Two initial towers
and 100 colonists per faction are development starting conditions. `P` switches
between two human-controlled factions. There is no AI, battle-budget scheduler,
combat building targeting, tower-loss redistribution, automatic victory/campaign
flow, native save/load, diplomacy, or nuclear detonation/interception. Nuclear
arming is disabled. `N` explicitly starts the next island with new initial state.
The existing verified casualty primitives do not constitute a complete battle.

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

The launcher prefers the local native D81, selects a 1581 drive for D81 images,
and enables virtual-device turbo loading by default. `VICE_TURBO_FLOPPY=0`
selects true drive emulation. Pass an explicit D64 path to run the old game.
`LOAD"NGSTART",8,1` followed by `RUN` starts the development UI directly.

## Controls

| Key | Action |
|---|---|
| WASD / port 2 joystick | Select sector |
| Enter / fire | Select army source, then an adjacent land destination |
| U / H | Deploy ten idle people as unarmed troops / return army to its own tower |
| M / J | Add/remove miner on selected deposit |
| R / K | Add/remove inventor on selected design |
| C / E | Cycle design category (shield, defence, attack) / design age |
| T | Select mine, laboratory or factory construction |
| B / V | Add/remove construction worker |
| F / G | Add/remove factory worker; production uses an unlimited queue |
| X | Arm one researched attack unit; early ages pay resources, later ages use inventory |
| [ / ] | Select deposit |
| Space / 1,2,3 | Pause / simulation speed 1x, 3x, 9x |
| P | Change human faction |
| N | Discard current island and load next development island |
| Z | Play first original voice clip (audio integration check) |

Original rules enforce recipe affordability, construction progress, research,
technology, mining exhaustion, births, manufacturing and neutral tower completion.
Commands enforce ownership and adjacency. Research beyond age 5 requires a lab.
Movement is immediate; the original travel UI is not implemented. Building and
army artwork uses the existing converted sprites; the small island picture uses
a hires character conversion of the original atlas. It preserves silhouettes
and dominant character-cell colours, rather than the complete original palette.
The board and interface still differ substantially from DOS.

## Memory and loading

| RAM | Use |
|---|---|
| `$0400–$07FF` | Text screen and sprite pointers |
| `$0801–$08FF` | Standalone BASIC/ROM bootstrap |
| `$0900–$0FFF` | SID music, sample NMI, bounded sequential loader |
| `$1000–$27FF` | Core and world codec code |
| `$2800–$295F` | Hardware startup, IRQ and C wrappers |
| `$2960–$313F` | Command code |
| `$3140–$327F` | Four army walk frames and building sprite |
| `$3280–$32FF` | Keyboard/joystick reader |
| `$3300–$36FF` | Driver state, music tables, strings and clip metadata |
| `$3700–$37FF` | Cursor/source sprites |
| `$3800–$3FFF` | Charset; island picture uses glyphs 128–139 |
| `$4000–$68FF` | Sixteen compact sectors, 656 bytes each |
| `$6900–$6FFF` | Drawing code |
| `$7000–$7FFF` | 1,097-byte working sector, rule tables and C globals |
| `$8000–$BFFF` | Remaining native code and initialized data |
| `$C000–$C3FF` | C software stack |
| `$C400–$D3FF` | Resident SID music, including RAM beneath I/O |
| `$EF00–$FFF9` | Shared effect/voice cache, at most 4,346 bytes |

BASIC is banked out; KERNAL and I/O stay visible (`$01=$36`). Sample fetches
briefly reveal underlying RAM and restore the port. The two NMI vector bytes at
`$FFFA/B` lie beyond the cache. The native core is ordinary 6502 code; no original
x86 code is embedded or executed in the C64 runtime.

Each compact sector preserves fields consumed by the verified core and the
island's legal age window (up to four ages). Tower timers encode a fixed deadline
and worker-derived rate. DOS rendering fields and out-of-window unit/inventory
fields are omitted. This is not yet a complete save format for unported rules.
Python and C codecs are checked against each other for every legal age window
and all sixteen slots, including active tower construction.

`NGTABLE` has magic `NGR1` and exactly 596 rule bytes. `NMAPnn` uses `NGW2`,
first/last age, sixteen terrain IDs, an RLE-compressed 96-byte picture, twelve
colour bytes and an RLE-compressed 10,496-byte world. `NSPRnn` has `NGP1` plus
320 compressed sprite bytes. `NSNDnn` has `NGS1`, a little-endian nibble count,
a voice flag and compressed packed PCM. All RLE writes have exact output bounds;
truncated input fails, including a missing final byte. Required world/sprite
failures stop with an error screen. Audio failures leave playback disabled.

Code files include two-byte load addresses. Stream files have no load addresses.
The D81 writer uses lowercase host-side directory arguments because `c1541`
converts those to the uppercase ASCII/PETSCII bytes requested by the runtime.
The disk has room for the intro, all 28 islands, ten sprite sets and nineteen
full audio clips. Generated content is not included in source releases.

## Verification

```sh
python3 -m unittest discover -s tests -p test_native.py -v
python3 tools/verify_native.py \
  --disk ../recovery/MegaLoMania64_native.d81 \
  --native ../recovery/native --out ../recovery/native/check-pal \
  --model pal --handoff
```

Use `--model ntsc` for NTSC. The isolated VICE check exercises the existing PRG's
handoff, required disk loads, sprite bytes, resident score, deployment/return,
inventor allocation, hotseat switching, another island and streamed voice cache
bytes. It checks that immutable native code remains unchanged. Screenshots,
RAM dumps and a monitor transcript stay in the private output directory.
This check does not establish complete game correctness or exact DOS graphics.
