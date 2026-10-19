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

Sprite colour mapping: dark → black (`$D025`), light low-saturation → light grey (`$D026`), coloured clothing/brick → the owner's colour (per-sprite). The galaxy is mapped by brightness onto black / blue / light blue / cyan / white with an ordered dither.

## Choices that are this port's, not recovered data

* Which sheet row is shown for which epoch (`ARMY_STRIPS` in `tools/orig_convert.py`) and which building cell goes with which epoch.
* Slot 28 of the island names is "THE MOTHER" (from the original "the mother / of battles" strings); the original text refers to island 27 as MEGALOMANIA.

## Not used (not decoded by anyone yet)

The 54 `.DAT` files (maps, tech tree, balance, speech, music) — the reverse-engineering package states that no compression signature is proven and no decoder exists. Nothing was guessed or fabricated from them. The remaining ILBM sheets (`ISLANDS`, `MSLANDS`, `MRMIES`, `MUILDS`) are not converted yet; the island map tiles stay the port's own character graphics.

## Licence note

The original art and text are the property of their rights holders. This project is an unofficial fan port. Converted derivatives are committed for build reproducibility; check the licensing situation before distributing the project publicly. The engine includes `assets/orig/army_frames.bin` and `build_icons.bin` directly, so removing the derivatives means replacing them with your own sprite data of the same layout (10 × 4 × 64 and 10 × 64 bytes).
