# Disk save format v4 — engineering specification

## File and DOS sequence

1. `S0:ML64SAVE` is sent over command channel 15 (`SETLFS 15,dev,15` · `SETNAM` · `OPEN` · `CLOSE`) to scratch any previous save. The old `@0:` save-and-replace is **not** used (unreliable on some 1541 firmware).
2. `SETLFS(1,dev,1)` · `SETNAM "ML64SAVE"` · `SAVE` with zero-page pointer `$FB` → `$C000`, end = `$C000 + 8 + N`.
3. **Verify:** `SETLFS(1,dev,0)` · `SETNAM` · `LOAD` with A=1 (KERNAL VERIFY) against the staged buffer, then `READST`; only `$40` (EOF) is accepted (`status & $BF` must be 0). Failure ⇒ `DISK/SAVE ERROR - STATE UNCHANGED`.
4. Load: `SETLFS(1,dev,0)` (secondary 0 ⇒ KERNAL uses X/Y = `$C000`, never the file header), `LOAD` A=0, carry check, returned end address check, `READST` check, then snapshot validation.

`dev` = `$BA` (the device the game was loaded from) when it is 8–11, else 8. Screen and sprites are off and `$D011` bit 7 is kept 0 for the duration (`disk_begin`/`disk_end`); interrupts are re-enabled on every exit path.

## Payload at `$C000`

| Offset | Bytes | Meaning |
|---|---:|---|
| 0 | 4 | ASCII `ML64` |
| 4 | 1 | **Version = 4** |
| 5 | 1 | N = `cpu_count + 1 - owner` |
| 6 | N | State bytes from label `owner` through `cpu_count` inclusive |
| 6+N | 1 | XOR of state bytes |
| 7+N | 1 | Additive checksum mod 256 |

The state block starts with the 13 sector arrays, then **`truce[5]` and `truce_cool[5]`** (new in v4, indexed by faction id), then campaign and runtime scalars. Island terrain, sprites and graphics are never saved.

## Validation (before anything is applied)

Signature, version 4, length N, both checksums, campaign < 28, selected/source < 12, state < 5, every `truce` ≤ `TRUCE_TICKS` (90) and `truce_cool` ≤ `TRUCE_COOL` (60), and per-sector ranges (owner ≤ 4, people ≤ 90, ore ≤ 95, miners/labs ≤ 12, level ≤ 5, weapons ≤ 90, fort ≤ 9, buildings ≤ 7, minegrade ≤ 2, policy ≤ 3, doctrine ≤ 2). Version-3 files are rejected. `frames_per_tick` is recomputed from `$02A6` on load.

## Limits

No cryptographic integrity; the KERNAL itself has no maximum-length guard on `LOAD`, so load only game-created files. Tested against a KERNAL **model** (including a write-protected-disk case where `SAVE` looks successful and only the verify catches it); **not** yet against a real or emulated 1541.
