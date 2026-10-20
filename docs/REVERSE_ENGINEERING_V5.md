# Local v5 reconstruction — evidence and reproduction

The original v5 cloud checkout was not recovered. This implementation starts at
v4.4 commit `0285c58359574a385788af084f643ef2eb0e15ce` and uses the owner's
`MegaLoMania_Reverse_v11_EVIDENCE_AND_PROBES.zip`. Generated original files and
full disks are kept in the sibling `../recovery/` folder, outside this checkout.
The development source was pushed on 20 October 2026; the original-derived full disk remains local.

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

`make_music.py` now retains all four source channels, note onsets, speed and
pattern breaks, and quantized volume slides. ProTracker volume-slide upper-nibble
priority follows the original [replayer](https://github.com/8bitbubsy/pt2-clone/blob/master/src/pt2_replayer.c). Title `choose3` and game `war14` load as separate `MLM2`
banks (`MUSIC` / `MUSICG`). Channels 0/1 alternate on SID oscillator 1; channels
2/3 have dedicated oscillators. All four parts are represented, with a characteristic
SID arpeggio where two original voices sounded simultaneously. Sample timbres are
approximated by SID waveforms; dynamics use 16 sustain levels and finetune rounds
to semitones. This is still an arrangement, not a byte-identical Paula replay.

The title bank is loaded before the streamed introduction, so it plays during
scene holds. The game bank extends into RAM beneath I/O. Music runs at a 50 Hz
timebase on PAL and NTSC. Noise percussion uses short zero-sustain decays rather than continuous noise.
Each rendered voice restores its complete frequency,
pulse, waveform and ADSR state after UI effects or digis. Notes arriving while a
UI effect owns oscillator 1 remain in the virtual-channel state and resume afterward.

`EFFECTS` contains all eleven complete original Amiga effects, without the old
0.4/0.5-second clipping. It replaces a padded 9000-byte main bank and uses a second
3072-byte region beneath I/O at `$D400`. Playback crosses this boundary at the
exact byte address, including a non-page-aligned boundary. The original clipped
bank remains the optional-file fallback. An interrupted full-bank load disables
partially overwritten digis and falls back to tonal effects.

Sample playback detects the SID revision from oscillator 3 combined-wave output.
It uses one DC pulse with TEST/gate on 6581 and three on the quieter 8580, giving
the volume DAC an input on an unmodified C64C. All TEST bits and envelopes are
restored afterward. A nested NMI during a banked read temporarily maps I/O in
to acknowledge the real CIA rather than its hidden RAM. The configuration
follows the original [C=Hacking digi article](https://raw.githubusercontent.com/Jeff-Birt/C64_DIGI/master/the_c64_digi.txt).
Explosion/grunt/fanfare effects precede queued spoken reactions; the voice no longer
silently replaces the effect. Both are mono, sequential playback. No simultaneous
Paula-style sampled mixing is claimed.

## What the full disk implements

`SCENE01`–`SCENE14` reproduce the four V1E–V4E stories in the DOS order.
Each story starts with its original 320×200 view; after 250 source retraces, a
39-pixel text strip from y=200, 239, or 278 replaces y=161–199. The four stories
have 3, 3, 4, and 4 stages. Only the changing bottom 40-pixel cell band is stored
for later stages, keeping the complete introduction on one D64.

`SCENE15`–`SCENE29` contain the V5E–V19E credits. All 320×600 source pixels remain
in the converter; there is no center crop or resize. Black-background hires
characters preserve the 320-pixel lettering, with a best-fit C64 ink per cell.
Each card has 21–242 distinct glyphs, fitting a 256-character set. The viewport
scrolls upward over 160 pixels of screen; a separate 40-pixel logo stays below.
The recovered scroll counts are 328,328,344,240,240,240,240,320,390,376,390,360,
390,290,130. A nominal 70 Hz logical clock runs on both PAL and NTSC, advancing
one or two source ticks per physical frame. It preserves the recovered count and
average speed; it cannot reproduce every 70 Hz VGA frame on a 50/60 Hz VIC.
DOS palette fades and disk-load pauses are not cycle-exact reproductions.

`tools/intro_timeline.py` verifies the executable SHA-256, exact instruction
bytes, initial 40-byte scanline stride / 1600-byte display start, and scroll table
before asset conversion. `tools/trace_dos.py` optionally runs the original x86
instructions under Unicorn to corroborate the resource order and retrace calls.
Its virtual DOS writes do not modify the original resources. This diagnostic
models neither VGA timing nor the original game interrupts, so it does not prove
original AI/economy/combat behavior.

The optional image tools need Pillow and NumPy. Normal assembly needs neither.
Story art uses 20 multicolour character rows above five hires rows of text. Hires
conversion minimizes Oklab error and keeps neutral source pixels on the neutral
C64 ramp. Multicolour cells optimize three local colours against black. Physical
VIC colour/cell constraints still limit fidelity.

The runtime holds split-mode scenes without IEC reads, since serial transfers
mask IRQs. It blanks during the next load. Credit text uses bank 3 and switches
to one of two fixed logo placements according to the VIC row counter; this avoids
moving the logo with the text's fine scroll. Intro-only code occupies `$5100`
and a disk-read callback stays resident at `$0E80`, because speech later replaces
the intro RAM. The original sprite-source RAM is preserved.

`MLI1` modes 0/1/2 have 8000/1000/1000-byte bitmap/screen/colour segments;
mode 3 has 2048/3000/3000/1600/200-byte charset/map/ink/logo/screen segments;
mode 4 changes only 1600/200/200 bytes at the bottom of the current story.
Every segment has bounded RLE decoding, and credit counts above 400 are rejected.
Any key or FIRE skips; missing content falls back to the native title. `TITLE`
restores the embedded bitmap after reuse. The older native title/parade remains
before the fan strategy engine, so the whole boot sequence is not the DOS UI.

The sunrise palette evidence remains in `tools/exe_palette_evidence.py`: the
startup table changes SUNRISE to MUNRISE, and code copies the 48-byte RGB6 table at
EXE `$3326` to DS:`$5236`. That resource is not inserted after the credit roll.

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
rejection. The full disk has 62 content files plus the main PRG. Save/load retains
its v4 snapshot format and `$C000` buffer.

## Reproduce

Extract the supplied archive outside the source checkout; set `DOS` to its `dos`
folder and `ADF` to the good Amiga disk image. From this checkout:

```sh
python3 tools/recover_original.py --dos "$DOS" --out ../recovery/decoded
python3 tools/recover_amiga.py --adf "$ADF" --out ../recovery/amiga_recovered
python3 tools/orig_convert.py --orig ../recovery/amiga_recovered --samples-only --effects-out ../recovery/content
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

Cycle-exact intro palette transitions and VIC split behaviour; exact VGA refresh
on 50/60 Hz hardware; faithful four-channel sampled timbre on SID; gameplay object layouts, campaign
terrain, AI, economy, combat and balance; raw resource semantics; real hardware
IEC timing and 6581/8580 audio quality. The strategy simulation remains the fan
port's existing engine. A decoded file alone is not proof that any of these game
systems has been ported.

## Further executable evidence

The credit order comes from DS:`$453A`, V5E through V19E. File `$11A37` selects
DS:`$455A` and DS:`$453C`; `$11A3F` adds 160 to each signed table word. The words
actually begin at `$455A`, not `$4558`: 168,168,184,80,80,80,80,160,230,216,230,
200,230,130,-30. The earlier notes included a preceding zero and missed -30.
File `$11AF2` sets CRTC 0C/0D; `$11AFF` adds DS:`$AF7F` (40 in the traced
16-colour mode) once per call to `11B9:0C58`. That routine at file `$13DE8`
waits on port `$3DA`, bit 3. The initial display start is 1600 bytes, or 40 rows.
CRTC line-compare 320, with double-scanned source pixels, leaves a 160-pixel
viewport above the fixed logo. Runtime tracing corroborates every card distance.

The story helper at file `$1FA34` copies `$618` (1560) bytes from SI to video
address `$1928`: 39 scanlines × 40 bytes, destination y=161. Its calls use SI
`$1F40`, `$2558`, `$2B70`, corresponding to y=200/239/278. The outer loops load
CX=250. These are executable-derived values, not estimates from screenshots.
