# Disk save format v3 — engineering specification

- CBM DOS save name: `@0:ML64SAVE` (replace syntax). CBM DOS load name: `ML64SAVE`.
- Save uses KERNAL `$FFBA` SETLFS(A=1,X=8,Y=1), `$FFBD` SETNAM, `$FFD8` SAVE(A=$FB,X/Y=end exclusive). The save start address is `$C000` stored in zero page `$FB/$FC`.
- Load uses SETLFS(A=1,X=8,Y=0) (force relocation to X/Y address `$C000`) and `$FFD5` LOAD(A=0,X/Y=$C000). KERNAL carry indicates I/O status; returned X/Y must equal expected exclusive end.
- Saved PRG file begins with load address little-endian `$C000`. The in-memory payload at `$C000` has:

| Offset | Bytes | Meaning |
|---|---:|---|
| 0 | 4 | ASCII `ML64` |
| 4 | 1 | Version = 3 |
| 5 | 1 | Snapshot byte length (`cpu_count + 1 - owner` in symbol table) |
| 6 | N | Exact state bytes from assembler label `owner` through `cpu_count` inclusive |
| 6+N | 1 | XOR of state bytes |
| 7+N | 1 | Additive byte checksum modulo 256 |

The remaining bytes in the source code, immutable island terrain data, sprite and graphics are never saved. Loading first checks signature, version, length, XOR/sum, per-sector ranges and campaign stage. It then reconstructs map/epoch-dependent graphics and restores the backed-up RAM state. `frames_per_tick` is recalculated from `$02A6` for the current machine.

Limitations: no cryptographic integrity, no safe maximum-length limit at the KERNAL LOAD API layer, and DOS `@` replacement has compatibility/old-drive caveats. Store only trusted save files on a writable image/disk. The unit tests exercise deterministic opcodes and a KERNAL mock, *not a running 1541 emulator*. Restore from corrupted file must not alter the live campaign as long as loader did not overwrite other program memory.
