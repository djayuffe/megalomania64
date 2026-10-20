# Original data: what was used

Source: *MegaLoMania_Reverse_v11* (a reverse-engineering package of the 1991 PC release, supplied by the project owner). The files are **not** part of this repository (`original/` is git-ignored and left out of the release ZIP). Point the converter at a local copy:

    python3 tools/orig_convert.py --orig original/      # needs Pillow
    python3 tools/make_intro.py && python3 tools/gen_tables.py

The converted results are committed in `assets/orig/` so a normal build needs neither the originals nor Pillow.

## Used

| Original | Reader | Converted to |
|---|---|---|
| `MTARFLD.LBM` — galaxy picture, 320x256, 16 colours | `orig_import.load_ilbm` (checked pixel-for-pixel against the package's own PNG decode) | `assets/orig/galaxy_c64.png` → intro bitmap (rows 58–175) |
| `ARMIES.LBM` — 16x16 soldier frames | same | `assets/orig/army_frames.bin`: 10 epochs × 4 frames, 12x21 multicolour sprites (soldier = 8x16 multicolour pixels) |
| `BUILDS.LBM` — building cells (64x60) | same | `assets/orig/build_icons.bin`: 10 icons, scaled to 12x21 multicolour |
| `MEGA.EXE` — text tables | `orig_import.exe_text_tables` | `assets/orig/orig_text.json`: island names (26 + finale), epoch labels, rank titles, element names (with file offsets); island names are shown on the HUD |

| Amiga ADF carves, `amiga_8svx/original_*_8SVX.iff` — 8SVX sound effects (stick, throw, musket, machine gun, cannon, missile, laser, explosion, grunt, orchestra hit, timpani) | `orig_import.load_8svx` | `assets/orig/samples.bin` (+ `samples.json` index): mean removed, resampled to 5 kHz, soft-limited and error-diffused to 4 bit, packed two per byte (8401 bytes). Played through the SID master volume by an NMI player (v4.4) |

Historical v4.4 assessment (superseded by the v5 sector recovery below): the Amiga disk carves appeared fragmented — the **samples** are intact (8SVX has no compression here) but the carved ILBM **images** are garbled, so only the PC pictures above are used. The original *intro sequence* is therefore **not** recovered: the intro in v4.4 is a new sequence made of the decoded original art (galaxy, soldier sprites) and sounds. The Amiga music score is not available either; the tunes stay this port's own.

Sprite colour mapping: dark → black (`$D025`), light low-saturation → light grey (`$D026`), coloured clothing/brick → the owner's colour (per-sprite). The galaxy is mapped by brightness onto black / blue / light blue / cyan / white with an ordered dither.

## Choices that are this port's, not recovered data

* Which sheet row is shown for which epoch (`ARMY_STRIPS` in `tools/orig_convert.py`) and which building cell goes with which epoch.
* Which sample goes with which event: attack = the epoch's weapon (stick, stick, throw, throw, musket, musket, machine gun, cannon, missile, laser), capture = explosion, sector lost = grunt, repulsed = musket, victory = orchestra hit, defeat = timpani. Clip lengths (0.09–0.5 s) and the 4-bit/5 kHz quality are the C64 limits, not the original's.
* The eight soldiers of the intro parade are epochs 0–7 of the army sheet (epochs 8 and 9 are only in the game).
* Slot 28 of the island names is "THE MOTHER" (from the original "the mother / of battles" strings); the original text refers to island 27 as MEGALOMANIA.

## v5 resource reconstruction

The 54 DAT files and 38 voice files now decode through `tools/lzhuf.py`.
All 101 non-EXE/non-sidecar DOS resources have been processed; all 85 IFF files
validate through the ILBM/PBM/8SVX readers. See `REVERSE_ENGINEERING_V5.md` for
executable evidence, manifest reproduction, scene conversion and known gaps.

The optional full D64 uses V5E–V19E, V1E–V4E, VH/MUNRISE, eight voice clips and
28 tiles from ISLANDS.LBM. Generated content stays outside the source checkout.
The Amiga disk layout is now recovered as 510 payload bytes followed by a two-byte
footer in each sector. Removing these recovers 21 ILBM images, 20 8SVX sounds and
two valid MOD modules, `war14` and `choose3`. The 11 committed effects are regenerated
from the corrected sample bytes. The full disk includes a three-voice SID arrangement
of both scores; sample timbres and continuous volume fades are approximated and
one Amiga channel is omitted. Exact intro animation/timing and gameplay semantics
remain unresolved; raw image buffers are not recovered game maps or balance tables.

## Licence note

The original art and text are the property of their rights holders. This project is an unofficial fan port. Converted derivatives are committed for build reproducibility; check the licensing situation before distributing the project publicly. The engine includes `assets/orig/army_frames.bin` and `build_icons.bin` directly, so removing the derivatives means replacing them with your own sprite data of the same layout (10 × 4 × 64 and 10 × 64 bytes).
