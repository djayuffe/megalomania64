# Architecture v4 (VIC-II / 6510)

## Frame and tick model

`irq_install` (called from `start`) switches the CIA1/CIA2 interrupt sources off, points `$0314` at `irq_handler`, and enables only the VIC raster IRQ on line 250 (PAL and NTSC). One IRQ per frame:

1. acknowledge `$D019`; bump `vblank`;
2. write `$DC00 = $FF` (no keyboard column selected) and sample port 2 into `joy_raw`;
3. `sound_tick` — SFX sweep/gate timer and the 2-voice music sequencer (tune by epoch; 3 on the title; 4 victory, 5 defeat via `music_over`); then `fx_tick` — border flash, screen shake, sprite colour pulse;
4. if the title is up, arm the raster-bar stack; then `JMP $EA31` — the KERNAL keeps the jiffy clock and keyboard buffer alive.

`main_loop` sleeps in `wait_frame` until `vblank` changes, adds the elapsed frames (clamped to 8 after long disk I/O) to `frames`, and when `frames ≥ frames_per_tick` (16 PAL / 19 NTSC) subtracts the tick length **keeping the remainder**, then runs `simulate`. A slow frame therefore never loses time.

## Raster bars (title only)

Stage 0 picks a start line from a 32-entry wobble table and sets `irq_stage=1`. Stages 1..16 each write one colour to `$D020/$D021`, advance the compare line by 3 and leave through `$EA81` (register restore + RTI). Stage 17 restores the blue frame and re-arms line 250. They are **not** cycle-stable: expect a little edge jitter. The sequence is allowed to finish even if the title is dismissed mid-stack.

## Input

`read_keys` = KERNAL `GETIN`, else `read_joystick`. The decoder (see `src/joystick.asm`) turns stick edges, FIRE taps and debounced FIRE+direction chords into the equivalent key code, so there is exactly one command path. `key_extra` (in `develop.asm`) handles the v4 keys `E` and `U`.

## Rules engine

Unchanged from v3 (see `GAME_DESIGN.md`): `simulate` → economy, research, AI economy, AI turn; `do_attack` is shared by human and AI. v4 hooks: `rank_up_notice` after a rank-up, `diplo_tick` every tick, truce test in `ai_turn`'s target loop, `break_truce` in `player_attack`, `panel_extra` at the end of `panel_values`.

## Disk

See `SAVE_FORMAT.md`. KERNAL serial I/O runs with the display and sprites off (`disk_begin/disk_end`); the snapshot is staged at `$C000` so a failed validation never touches live state.

## Verification boundary

`tests/cpu6502.py` executes the shipped opcodes with: raster IRQ entry/RTI (`fire_irq`, `run_irq`, `run_for`), KERNAL `GETIN`, `SETLFS/SETNAM/OPEN/CLOSE/CLRCHN/SAVE/LOAD/VERIFY/READST`, port-2 pins, the live raster MSB in `$D011`, a write-protected disk, device numbers. It does **not** emulate VIC-II timing, badlines, sprite DMA, SID, CIA timers, IEC bit timing or 1541 DOS. A pass means the logic is right, not that the hardware agrees.

## Sound (v4.2)

`sfx_play` (A = id) drives SID voice 1 from nine parallel tables (`sfx_fhi/flo/sweep/wave/ad/sr/pw/len/prio`): start pitch, signed per-frame pitch sweep on the high byte, waveform, envelope, length and priority. A running effect is only replaced by one of equal or higher priority; the gate is dropped and raised again to retrigger the envelope. `beep_ok`/`beep_no` remain as wrappers. Voices 2/3 are the tracker: pulse lead with a pulse-width wobble and a sawtooth bass; every step releases both notes and re-gates them two frames later so repeated notes articulate. Six tunes of 16 steps (`tools/gen_tables.py`).

## Effects and HUD colour (v4.2)

`fx_flash` (A colour, X frames) alternates the border with the epoch colour (`border_tab`); `fx_shake_start` jitters `$D016` scroll while keeping the MCM and 40-column bits. `colorize_ui` recolours rows/segments of colour RAM after every score and panel redraw; HUD text may only use colours 0–7 (8–15 select multicolour glyphs and garble text — a regression test enforces it).

## Intro picture

`tools/make_intro.py` builds a 160x200 multicolour bitmap (committed under `assets/`). Background `%00` is black, so the raster-bar stack (which repaints `$D020/$D021`) shows through behind the logo. Row 22 (PRESS FIRE) is `%11`-only, so it colour-cycles through colour RAM.
