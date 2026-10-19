# Architecture v4 (VIC-II / 6510)

## Frame and tick model

`irq_install` (called from `start`) switches the CIA1/CIA2 interrupt sources off, points `$0314` at `irq_handler`, and enables only the VIC raster IRQ on line 250 (PAL and NTSC). One IRQ per frame:

1. acknowledge `$D019`; bump `vblank`;
2. write `$DC00 = $FF` (no keyboard column selected) and sample port 2 into `joy_raw`;
3. `sound_tick` — SFX gate timer and the 2-voice music sequencer (tune by epoch; tune 3 on the title);
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
