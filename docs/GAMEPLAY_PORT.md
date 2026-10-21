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
| Weapon crews and army manpower | `0D24:0F91` |
| Army arrivals, capacity, strength and leading-unit health | `1A17:165F` |
| Army casualties and cached strength | `1471:0FCD` |
| Neutral tower construction eligibility | `1471:05DE` |
| Turret installation, replacement and crew casualties | `0D24:1BCD`, `0D24:0E4E` |
| Random enemy-army targeting and damage resolution | `0000:5E55` |
| Random turret targeting and damage resolution | `0000:6154` |
| Gatherable-resource reconciliation and conversion tick | `11B9:108C`, `0D24:2336` |
| Whole-army extraction and demobilization | `11B9:1E18`, `11B9:1F93` |
| Tower completion and ownership installation | `0000:CD19`, `0000:5A9F` |
| Building removal and worker casualties | `0000:670B` |

The original population cap is 998. Worker productivity subtracts one worker for
every 32 assigned. Mining deposits and construction/research/manufacturing tasks
retain separate 32-bit progress. Reallocating workers on the same task preserves
progress. A substituted ingredient doubles research complexity. Manufacturing
pays for each unit; finite queues release workers on completion, while resource
shortages pause human production and stop computer production. Research points
are credited only once per design. Advancing from age 8 sets the special future
flag rather than incrementing the ordinary age.

Army arrivals admit higher-age units first, then unarmed units, up to 250 units
per faction per sector. Weapon crews are counted separately from units. A new
weapon type initializes its leading unit's health; reinforcements preserve that
unit's existing damage. Strength caches change with each arriving or lost unit.
Moving into neutral territory starts tower construction only when one active
army is present and its faction has no allies. A rival army contests that work;
defeating it permits construction to resume. Arrival does not transfer ownership.

Army damage picks an enemy faction uniformly, then a present weapon class
uniformly; it does not weight those choices by unit count. It carries unused
damage through casualties, resets health for the next unit of the same type,
and preserves the original random sequence when retrying depleted targets.
Turret damage retries draws among ten positions and removes crew and cached
strength on destruction. Allied and shutdown sectors are protected. The original
allied-turret early return yields the alliance predicate `1`, rather than the
incoming unused-damage budget; this observed quirk is preserved.

Nuclear arrival schedules the original flight timer and records its faction and
source sector. Detonation, retaliation and interception are not implemented yet.
The optional arrival branch controlled by DOS global `$1C78` is also untranslated;
the arrival comparisons explicitly set it to zero.

Gatherables have a separate raw-deposit quantity and total-stock quantity.
Conversion decreases the raw deposit without adding to total stock. Its buffer
selects rates of 775, 126 or zero at the original 20/40-unit boundaries, with a
2,400-tick deadline. Reconciliation accounts for stock spent before conversion,
preserves accumulated progress, and disables exhausted deposits using the
original timer representation.

The table extractor checks the exact executable hash and instruction signatures
before following pointers. It recovers all 28 island layouts, deposits for their
16 sectors, 20 element classes, 30 design templates, material groups, task bases,
technology dates, health tables and research/manufacturing tables. Original game
tables remain in the owner's private recovery folder.

The latest local run checked **448 campaign-sector initializations** for terrain,
owner, age, stock and active land deposits, plus **4,871 complete-sector rule
scenarios on both native backends**. The linked 6502 module is **16,272 bytes**
(3,747 at `$1000` and 12,525 at `$8000`).
The chained Aloha scenario allocates inventors, advances population and research,
finishes an actual recovered design, pays its resource cost and inventories an
early-age weapon. A second chain contests a neutral sector with two armies,
defeats the hostile army, resumes construction, and verifies the completed
tower's ownership and demobilized army. These are not full battles, islands or
campaign playthroughs.

Tower completion now installs the owner, returns the occupying army's weapons
to inventory and its crews to the population, then removes one idle person
from both population counts, as the original does. Inventory and population caps apply
independently. All factions' construction timers are cleared. Building removal
destroys its defenders and kills affected workers instead of returning them to
idle population: active deep miners in a mine, inventors on age-6-or-later
research in a lab, and workers manufacturing age-4-or-later items in a factory.
Original stale rates behind disabled task timers are preserved.

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

Output includes the raw code regions, two load-addressed PRGs, linker map/labels, host
library and `verification.json`. A failed verification removes any previous
success report. Output derived from the original must stay outside the checkout.
The audited executable SHA-256 is
`1f6d7bd92a8336818b65cc2157b5929dc353613258bfe8de6c83d23bb07a10ef`.
The local cc65 build used revision `8d86ca7`.

## Development ABI

This verification build links resident code in two regions: `$1000–$2FFF` for
military primitives and `$8000–$BFFF` for the remaining routines and compiler
helpers. State starts at `$5000`; the cc65 software stack is below `$C400`.
Both `core-low.prg` and `core.prg` must be loaded before calling `gp_run`, which
initializes that stack and calls `gp_dispatch`. Calls between the two code
regions are ordinary resident calls; there is no disk access per rule call.
This layout is **for verification**, and overlaps the current game's resident
code and audio/data layout. Loading it over the running game is unsafe.

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
| 24 (word) | Source sector ID for a nuclear flight |
| 26 (word) | Human owner ID for manufacturing shortage behavior |
| 28 (word) | Maximum island age for research advancement |
| 30 (word) | Active-faction bitmask for armies and construction |

Operations 0–17 are respectively: set idle population; birth tick; assign miners;
mining tick; affordable recipe count; pay recipe cost; add inventory; bounded
random; generic task rate/deadline; resource availability; assign builders;
construction tick; generate research recipe; assign factory workers; manufacture
tick; research tick; advance age; assign inventors. Callers must enforce valid
worker allocations, age/building unlocks and legal player actions as the original
UI does. Operations 18–25 count army manpower, remove an army unit, admit an army,
choose neutral-tower builders, install a turret, remove a turret, apply damage to
enemy armies and apply damage to turrets. For operation 24, the design-age field
at offset 6 instead gives the island's starting age. Damage operations return
unused damage at offset 12. Incoming units and unaccepted remainders use
`gp_army`; `gp_army_rules`, `gp_defence_rules` and `gp_alliances` supply military
tables and diplomacy. This module does not yet provide the command-validation layer.
Operations 26 and 27 reconcile gatherable stocks and tick their conversion,
respectively. Operation 27 also performs reconciliation after the tick.
Operation 28 extracts the faction given at offset 2 into `gp_army` and returns
its unit count. Operation 29 demobilizes `gp_army` into the current tower.
Operation 30 installs the owner given at offset 2 and demobilizes that army;
operation 31 ticks the selected neutral tower's construction. Operation 32
removes the building kind given at offset 4, including defenders and affected
workers. It is the removal primitive; the full tower-loss redistribution and
battle damage-budget scheduler are not implemented yet.

## Remaining work before a full gameplay port

- Finish equipment assembly and movement, building-damage targeting and
  tower-loss redistribution, the complete combat scheduler, alliance commands, computer decisions
  and nuclear interactions. Army/turret damage primitives are implemented;
  a complete battle has not been ported.
- Finish whole-world scheduling and connect the verified gatherable update.
- Implement the real campaign: deployment pool, choosing unfinished islands
  within an epoch, saved people, shutdown and the final battle.
- Compact the verified DOS records into C64 world storage, and budget code,
  graphics, music, effects and speech together. Sixteen full DOS records alone
  take 17,552 bytes; the existing game has only 105 bytes free below `$C000`.
- Replace the old sector UI and command handling, then validate full islands
  and campaign transitions in VICE on PAL and NTSC with audio enabled.

The default build and the existing full-content disk remain the intro/audio
development build described in `REVERSE_ENGINEERING_V5.md`.

The next original entry points to translate are building damage at `0000:6366`,
tower-loss redistribution at `0000:68F4`, and the full combat damage-budget
scheduler at `0000:5B10`. These have been located but are not implemented by
this module.
