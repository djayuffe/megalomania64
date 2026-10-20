# Local v5 reconstruction — evidence and reproduction

The original v5 cloud checkout was not recovered. This implementation starts at
v4.4 commit `0285c58359574a385788af084f643ef2eb0e15ce` and uses the owner's
`MegaLoMania_Reverse_v11_EVIDENCE_AND_PROBES.zip`. Generated original files and
full disks are kept in the sibling `../recovery/` folder, outside this checkout.
Nothing has been pushed or published.

## Proven resource format

The DOS resources have a four-byte little-endian decoded length followed by an
MSB-first adaptive Huffman/LZ stream. Parameters: 4096-byte history, maximum match
60, threshold 2; the first 4036 history bytes are spaces, the rest zero. Frequency
counts rebuild at 32768. The executable's MZ header is `$1600` bytes. The decoder
entry at load-image offset `$1EF60` is therefore file offset `$20560`. At entry
+$009F the executable fills `$0FC4` history bytes with `$20`; at +$00E6 it masks
the history cursor with `$0FFF`. These constants independently identify the codec.

The adaptive algorithm is consistent with the historical
[LZHUF implementation](https://github.com/e-n-f/lzss/blob/master/LZHUF.C).
`tools/lzhuf.py` is a new bounded Python implementation. Tests include the original
common compressed `FORM` prefix, literal streams through a frequency rebuild,
truncation, and an output-size bound. This is a decoder, not a byte-identical DOS
re-encoder.

All 101 non-EXE/non-sidecar DOS resources process successfully:

- 92 compressed resources: 54 DAT images/raw buffers and 38 voice clips.
- Seven existing uncompressed ILBM sheets.
- Two one-byte disk identifiers.
- Of these, 85 files are structurally valid IFF: 27 ILBM, 20 PBM, 38 8SVX.
- Sixteen are raw buffers/identifiers; successful decompression does not establish
  their gameplay semantics.

`recover_original.py` records source and decoded SHA-256 values in a manifest.
`orig_import.py` reads planar ILBM and chunky PBM and rejects malformed chunk,
ByteRun1 and image lengths. All 85 recovered IFFs pass the format readers locally.

## Amiga sector format and music recovery

Each 512-byte physical sector contributes its first 510 bytes to the logical payload;
the final two bytes are a footer. Joining those payloads, rather than carving physical
bytes directly, recovers 21 structurally valid ILBM images and 20 8SVX sounds. One
additional IFF candidate fails ByteRun1 validation and is explicitly rejected.
`tools/recover_amiga.py` records physical/logical offsets and SHA-256 values.

Two complete four-channel ProTracker modules also recover: `war14` at physical
`$1C00` (230044 bytes, 20 orders, 19 patterns) and `choose3` at `$59600` (12902 bytes,
12 orders, four patterns). `openmpt123` independently accepts both; their durations
are 145.92 and 107.52 seconds. The source archive contains only extraction tools;
the owner's recovered MODs stay outside the checkout.

`make_music.py` preserves note onsets, speed changes, pattern breaks and fade-to-zero
gates as compact events. Its calculated durations match OpenMPT. Three SID voices
arrange Amiga channels 1–3; channel 0 is omitted, sampled timbres become selected
SID waveforms, continuous volume fades become note gates, and sample finetune is
not reproduced. Thus these are original-score arrangements, not Paula emulation.
The 1888-byte resident bank includes separate PAL/NTSC frequency tables and plays
at a 50 Hz timebase on either video standard. The title uses `choose3`, the game
uses `war14`; victory/defeat retain the port's original cues. UI effects retain
voice-one priority; digis pause the sequencer and restore it afterward.

The 11 existing Amiga effect samples have also been regenerated from the corrected
IFF payloads using `orig_convert.py --samples-only`, eliminating injected footer
bytes from the v4 source carves.

## What the full disk implements

`SCENE01`–`SCENE15` contain V5E–V19E credit cards; `SCENE16`–`SCENE19` contain the
four V1E–V4E story panels, including their original rasterized text. `SCENE20`
composes the VH logo with the decoded packed-nibble MUNRISE image. The sunrise
palette is a plausible 16-entry, six-bit RGB table at EXE file offset `$3326`;
its rendering has been visually inspected, but its runtime code reference remains
to be established. Credit cards are vertically reframed around their content;
180/360-frame holds are port choices, not recovered original animation/timing.

C64 hires preserves 320-pixel lettering, with two nearest mapped C64 colours per
8×8 cell. The runtime alternates between VIC banks 1 and 3, loading the next scene
while the current one is displayed. Each file has a validated `MLI1` header and
three separately bounded RLE segments (8000 bitmap, 1000 screen, 1000 colour bytes).
Any key or FIRE skips; optional-content failure falls back to the native title or
returns to the game. `TITLE` restores the embedded bitmap after bank reuse.

`SPEECH` contains eight complete DOS clips (ARCONQ, FDEST, DESREADY, AWANNA,
PVERYW, NOWAY, LAFF, ARWON), resampled to 4 kHz and error-diffused to four bits.
Its 32-byte index is validated as a contiguous sequence within the reserved RAM
regions before playback is enabled. Clip events cover capture, loss, invention,
victory, defeat, and a question/answer queue for diplomacy. Playback uses the CIA2
NMI player and switches KERNAL out only for the sample-byte fetch. The original
Amiga weapon effects remain at 5 kHz. Disk access stops the NMI player.

`ISL01`–`ISL28` contain two multicolour sprites from each 48×16 ISLANDS.LBM atlas
cell. These are displayed on an island-entry card with the original island name,
number and epoch, and then restore the VIC registers and redraw the game. Atlas row-major association with campaign slots is a port choice;
original map/terrain/economy semantics have not been recovered.

The D64 builder supports chained directory sectors, DOS-style data interleave 10,
PRG and SEQ files, allocation/chain/EOF/BAM validation, duplicates and disk-full
rejection. The full disk has 51 content files plus the main PRG. Save/load retains
its v4 snapshot format and `$C000` buffer.

## Reproduce

Extract the supplied archive outside the source checkout; set `DOS` to its `dos`
folder and `ADF` to the good Amiga disk image. From this checkout:

```sh
python3 tools/recover_original.py --dos "$DOS" --out ../recovery/decoded
python3 tools/recover_amiga.py --adf "$ADF" --out ../recovery/amiga_recovered
python3 tools/orig_convert.py --orig ../recovery/amiga_recovered --samples-only
python3 tools/make_music.py --amiga ../recovery/amiga_recovered --out ../recovery/content
python3 tools/make_scenes.py --decoded ../recovery/decoded --dos "$DOS" --out ../recovery/content
python3 tools/make_speech.py --decoded ../recovery/decoded --out ../recovery/content
python3 tools/make_levels.py --decoded ../recovery/decoded --out ../recovery/content
python3 tools/build.py --test --preview --package --content ../recovery/content --full-d64 ../recovery/MegaLoMania64_full.d64
python3 tools/verify_vice.py --disk ../recovery/MegaLoMania64_full.d64 --out ../recovery/vice/full
```

A normal `tools/build.py` produces the source-checkout D64 without optional
original scenes/voices/island files and uses the existing title/effects.

## Remaining reverse engineering

Original intro viewport scrolling, transitions, exact palette references and
scene timing; faithful four-channel sampled timbre on SID; gameplay object layouts, campaign
terrain, AI, economy, combat and balance; raw resource semantics; real hardware
IEC timing and 6581/8580 audio quality. The strategy simulation remains the fan
port's existing engine. A decoded file alone is not proof that any of these game
systems has been ported.

## Further executable evidence

The original credit-file order is established from the EXE's DS:`$453A` table,
not inferred from filename order: V5E through V19E. File `$11A37` loads DS:`$455A`
and DS:`$453C`; `$11A3F` loads a scroll parameter and adds 160. The routine at file
`$11AF2` writes CRTC display-start registers 0C/0D; `$11AFF` advances the display
address by DS:`$AF7F`. The far call `11B9:0C58` resolves to file `$13DE8`, where
reads of port `$3DA`, bit 3, wait for a vertical-retrace edge. Consequently the
original credits really scroll on retrace; this port still displays reframed static
cards. The parameter words are 0,168,168,184,80,80,80,80,160,230,216,230,200,230,130.
Runtime video-mode stride/scaling remains to be established before claiming exact
motion and timing. Local evidence is in `../recovery/exe_intro_evidence.json` and
`exe_intro_disassembly.txt`.
