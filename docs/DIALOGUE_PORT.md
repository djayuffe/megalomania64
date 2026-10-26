# Character-specific diplomacy presentation

The native game now uses each original faction's face and separate offer,
acceptance and refusal recordings. `tools/dialogue_assets.py` reads the
owner-supplied executable's DS:AD74 filename table using dialogue bases
8, 22, 79 and 15. These are the IDs emitted by the recovered diplomacy state
machine, not a new random voice selection.

| Faction | Offer | Acceptance | Refusal |
|---|---|---|---|
| 1 | DJOIN | DWHY | NO |
| 2 | AWANNA | ASISI | ANOWORK |
| 3 | PMYTEAM | PVERYW | PNO |
| 4 | MYSIDE2 | YOUGOTIT (missing source) | NOWAY |

The original assets supplied with this checkout contain 11 of these 12 files.
The build records availability in private `dialogue.json` and `build.json`.
Missing YOUGOTIT is represented by a zero-length stream, so the visible
acceptance continues without playing a different character's recording. A
future rebuild automatically includes it if that original file is supplied.

Portrait descriptors come from DS:2DB8; their source pixels are in ICONS.DAT.
The converter validates the original descriptor segment/pitches and reads each
full 35–48 by 50–56 pixel face. It converts it to a 32 by 32 hires portrait with
16 character inks. It uses the game palette and preserves each complete face;
layout, resolution and palette precision are C64 adaptations. Talking-mouth
animation is not included in this change.

The ninth leaf overlay, `NGPRES`, occupies the existing EF00 window. Each
`NFACnn` file contains NGH1, 128 compressed glyph bytes and 16 literal ink bytes.
The glyphs use `$3F80–$3FFF` (codes 240–255), which the terrain converter reserves.
The portrait appears in a four-by-four panel during negotiation. Save metadata
also uses these glyph slots temporarily; persistence and island graphics loads
invalidate the portrait cache, and the next dialogue draw reloads the face.
Only 16 ink bytes and the cache identity stay resident. Resident music and the
world are untouched.

Voices use existing bounded 4-bit/4 kHz playback in separate NSND20–31 files.
Each complete clip fits the existing 4,346-byte audio window; none is truncated
to fit. Audio replaces presentation code only after the leaf returns. Invalid
speaker/dialogue combinations return no clip, preventing another faction's
voice from being played. Portrait filenames are resident because KERNAL file
opening exposes ROM over the overlay address range.

Tests cover all 12 voice routes, invalid speaker/ID pairs, original descriptor
decoding, portrait glyphs/inks, shared audio/code cache behavior, gameplay and
selector regressions. `tools/verify_native.py --dialogue` exercises all four
faces, every available complete recording, visible portrait cells, restoration
after save/load, resident-music preservation and the ordinary native campaign
checks in VICE. Original-derived artwork and recordings remain private.

The 27 October build passes 99 focused tests and the complete native VICE
verifier with `--dialogue` on PAL and NTSC. Both runs verify 12 dialogue routes,
four exact portrait fonts, all 11 available complete recordings, portrait
restoration after persistence and unchanged resident music. The final rendered
portrait panel was inspected in VICE.
