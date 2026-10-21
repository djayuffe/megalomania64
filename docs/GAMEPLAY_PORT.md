# Original gameplay port: development status

The running disk still uses the older fan gameplay engine. The new rules core in
`src/gameplay/` is compiled and verified separately; it is **not connected to the
game UI or included in the release PRG**. This is an intermediate implementation,
not a completed gameplay port.

## Implemented and checked against the DOS executable

The new portable C routines compile to native NMOS 6502 code through cc65. The
verification harness runs each original x86 routine in Unicorn, runs its C and
6502 translations, and compares the entire 1,097-byte sector record after each
operation. It also compares returned counts, research recipes and random seeds
where relevant.

| Rule | Original entry point |
|---|---|
| Idle population and birth rate | `0D24:2890`, `11B9:1487` |
| Miner allocation and independent deposit depletion | `11B9:1378`, `11B9:1678` |
| Affordable recipe count and atomic resource payment | `0D24:2AF1`, `0D24:2BD5` |
| Inventory addition and 200-unit cap | `0D24:2DEF` |
| Bounded random numbers, including even-bound retry | `11B9:0EB1` |
| Worker rates and 32-bit deadlines | `11B9:11E8` |
| Resource access and stock availability | `0D24:194B` |
| Construction assignment, completion, health and turret slots | `11B9:15D8`, `11B9:183E`, `0D24:0A04` |
| Random research recipes and one permitted ingredient substitution | `1A17:0599` |
| Factory allocation and manufacturing | `1471:0187`, `0000:CE20` |
| Research completion and technology points | `0000:C950` |
| Age advancement and damaged-building health scaling | `0D24:13D7` |
| Inventor allocation and recipe installation | `1471:0000` |

The original population cap is 998. Worker productivity subtracts one worker for
every 32 assigned. Mining deposits and construction/research/manufacturing tasks
retain separate 32-bit progress. Reallocating workers on the same task preserves
progress. A substituted ingredient doubles research complexity. Manufacturing
pays for each unit; finite queues release workers on completion, while resource
shortages pause human production and stop computer production. Research points
are credited only once per design. Advancing from age 8 sets the special future
flag rather than incrementing the ordinary age.

The table extractor checks the exact executable hash and instruction signatures
before following pointers. It recovers all 28 island layouts, deposits for their
16 sectors, 20 element classes, 30 design templates, material groups, task bases,
technology dates, health tables and research/manufacturing tables. Original game
tables remain in the owner's private recovery folder.

The latest local run checked **448 campaign-sector initializations** for terrain,
owner, age, stock and active land deposits, plus **2,617 complete-sector rule
scenarios on both native backends**. The linked 6502 module is **9,421 bytes**.
The chained Aloha scenario allocates inventors, advances population and research,
finishes an actual recovered design, pays its resource cost and inventories an
early-age weapon. It is not a full island or campaign playthrough.

Unused fields in the original initializer are not assumed to be zero. In
particular, sea sectors may retain stale deposit quantities after reinitializing
an island; their inactive deposit IDs prevent those quantities being used.

## Reproduce verification

Portable synthetic regression tests need a host C compiler, with no DOS files,
Unicorn or cc65. They skip when no compiler is available:

```sh
python3 -m unittest discover -s tests -p test_gameplay_core.py -v
```

The differential suite additionally needs the owner's exact audited DOS files,
Python Unicorn, and a built cc65 source tree containing `bin/` and `lib/none.lib`:

```sh
python3 tools/verify_gameplay.py \
  --dos /absolute/path/to/original/dos \
  --cc65 /absolute/path/to/built/cc65 \
  --out /absolute/path/outside/the/checkout/gameplay-verification
```

Output includes the raw module, load-addressed PRG, linker map/labels, host
library and `verification.json`. A failed verification removes any previous
success report. Output derived from the original must stay outside the checkout.
The audited executable SHA-256 is
`1f6d7bd92a8336818b65cc2157b5929dc353613258bfe8de6c83d23bb07a10ef`.
The local cc65 build used revision `8d86ca7`.

## Development ABI

This verification build links code at `$8000`, state at `$5000`, and the cc65
software stack below `$C400`. `gp_run` initializes that stack and calls
`gp_dispatch`. This layout is **for verification**, and overlaps the current
game's resident audio/data layout. Loading it over the running game is unsafe.

The byte arrays use explicit little-endian access. `gp_sector` retains the DOS
record layout so original state transitions can be compared without an adapter.
`gp_recipe` contains five element/cost pairs (`$FF` is unused). The other arrays
hold caller-supplied rule tables. Tests use synthetic tables; the differential
harness supplies audited extracted tables.

| Request offset | Meaning |
|---|---|
| 0 (byte) | Operation number |
| 2 (word) | Worker count, elapsed ticks, quantity or random bound |
| 4 (word) | Deposit slot, building kind or design category |
| 6 (word) | Design age |
| 8 (word) | Production queue count; zero means continuous |
| 10 (word) | Random seed, updated in place |
| 12 (word) | Returned count, affordability, complexity or worker rate |
| 14, 16 (words) | Generic task base and scale inputs |
| 18 (word) | Recipe variant: 1 canonical, 0 substituted/failed |
| 20 (byte) | Native notification bits for exhausted deposits/completed tasks |
| 22 (dword) | Generic task deadline output |
| 26 (word) | Human owner ID for manufacturing shortage behavior |
| 28 (word) | Maximum island age for research advancement |

Operations 0–17 are respectively: set idle population; birth tick; assign miners;
mining tick; affordable recipe count; pay recipe cost; add inventory; bounded
random; generic task rate/deadline; resource availability; assign builders;
construction tick; generate research recipe; assign factory workers; manufacture
tick; research tick; advance age; assign inventors. Callers must enforce valid
worker allocations, age/building unlocks and legal player actions as the original
UI does. This module does not yet provide that command-validation layer.

## Remaining work before a full gameplay port

- Recover and translate armies, equipment crews, movement, combat, damage,
  capture, alliances, computer decisions and nuclear interactions.
- Finish gatherable-resource reconciliation and whole-world scheduling.
- Implement the real campaign: deployment pool, choosing unfinished islands
  within an epoch, saved people, shutdown and the final battle.
- Compact the verified DOS records into C64 world storage, and budget code,
  graphics, music, effects and speech together. Sixteen full DOS records alone
  take 17,552 bytes; the existing game has only 105 bytes free below `$C000`.
- Replace the old sector UI and command handling, then validate full islands
  and campaign transitions in VICE on PAL and NTSC with audio enabled.

The default build and the existing full-content disk remain the intro/audio
development build described in `REVERSE_ENGINEERING_V5.md`.
