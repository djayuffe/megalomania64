# Original gameplay port: development status

The private native D81 integrates the translated rules into a playable C64 game
with battles, computer opponents, hotseat, diplomacy, nuclear weapons, campaign
progression and resilient disk saves. The fallback D64 still uses the older fan
engine. Movement reachability, deployment populations/order, alliance group operations and
AI economy planning/goal selection now use translated DOS rules. Tactical army
choices, negotiation decisions, deployment interaction timing and the interface
still include C64 policy. Explicit and automatic future shutdown, saved people, deployment pools and
within-epoch island selection are now integrated. See [native integration](NATIVE_INTEGRATION.md).

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
| Full battle budgets and faction scheduling | `0000:5B10` |
| Facility targeting and damage | `0000:6366` |
| Tower-loss civilian and defender redistribution | `0000:68F4` |
| Intact turret recall and inventory/crew return | `1471:033C` |
| Nuclear detonation and automatic future protection | `0000:6EC4`, `0000:668F` |
| Shutdown and saved-population limits | `0000:6B6C` |
| Initial tower and deployment population | `0000:74C8` |
| Shield repair and building-health clamp | `0D24:1669` |

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
source sector. Detonation is translated; retaliation and interception are orchestrated by the native runtime.
The optional arrival branch controlled by DOS global `$1C78` only resumes
DOS pause/UI globals; additional arrival comparisons enable it. Native pause
handling uses the C64 interface.

Gatherables have a separate raw-deposit quantity and total-stock quantity.
Conversion decreases the raw deposit without adding to total stock. Its buffer
selects rates of 775, 126 or zero at the original 20/40-unit boundaries, with a
2,400-tick deadline. Reconciliation accounts for stock spent before conversion,
preserves accumulated progress, and disables exhausted deposits using the
original timer representation.

The table extractor checks the exact executable hash and instruction signatures
before following pointers. It recovers all 28 island layouts, deposits for their
16 sectors, 20 element classes, 30 design templates, material groups, task bases,
technology dates, health tables and research/manufacturing tables. Original per-island faction counts (two to four) are recovered from DS:2082,
whose indexed read and +1 are checked in the executable. Original game
tables remain in the owner's private recovery folder.

The local verifier compares all 448 campaign-sector initializations plus 15,988
rule/world-strategy scenarios on host C and native 6502. This includes
battle scheduling, building damage, tower loss, defence recall and ordinary
nuclear detonation. Chained scenarios cover Aloha research/resource payment and
contested occupation through tower completion. See the generated private
`verification.json` for exact counts and code sizes. These comparisons do not
establish human balance or an exact DOS campaign playthrough.

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

This verification build links resident code in three regions: `$1000–$2FFF` for
military primitives and `$8000–$BFFF` for the remaining routines and compiler
helpers, plus a combat bank at `$D400–$FEFF` with `$01=$34`. State starts at `$5000`; the cc65 software stack is below `$C400`.
The low/high PRGs and raw `core.bin.bank` at `$D400` must be loaded before calling `gp_run`, which
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
workers.

## Fidelity limits

The running C64 game supplies whole-world scheduling, equipment and movement,
AI, diplomacy, nuclear flight/defences, victory/campaign transitions and saves.
Its compact world storage, banked code, pictures and streaming audio coexist in
64 KB. These integrations are described in `NATIVE_INTEGRATION.md`.

Campaign preparation now provides a shared deployment pool, unfinished islands
within three-island epochs, starting-sector choice, saved future populations and
the final battle. Initial tower creation, explicit shutdown and automatic
shutdown on fatal tower damage or nuclear impact are checked against DOS.
Automatic shutdown preserves the original owned-count indexing quirk: when
owned-sector count is 0 or 1, the original indexes army-sector counts by that
count, rather than by faction. Its facility masks 1/2/3 are also retained.

AI army/tactical choices, diplomacy acceptance/proposals, deployment interaction
timing and the interface remain C64 adaptations. The extracted per-island
computer population and faction-order permutation tables replace fixed starting
allocations. Ground reachability, aircraft separation and alliance groups now
follow DOS. Original VGA presentation is converted to VIC character
colours. The optional arrival `$1C78` branch only resumes DOS pause/UI globals;
additional sector/RNG comparisons enable it. Native pause handling uses the C64
interface. Real hardware timing and human balance across every island require
further playtesting.

Operations 33–37 run the complete ordinary battle budget scheduler, building
damage, tower loss, intact turret recall and nuclear detonation. Scheduler
request offset 6 is the island's first age and offset 24 is its island index.
Original 16-bit arithmetic and the observed tower-loss zero-capacity quirk are
preserved. Native runtime rare routines use a disk overlay shared with audio;
the standalone verification module keeps all routines resident.

Operation 38 explicitly shuts down a sector and returns saved people at offset
12 (human free people +1, computer minimum 100, all capped at 500). Operation 39
creates the initial tower for faction at offset 2 and population at offset 4.
Automatic shutdown reports saved people at offset 18. Whole-world `gp_owned`,
`gp_retired` and `gp_army_sectors` arrays supply the original global counts.

Operation 40 repairs building at offset 4 with shield age at offset 6, returning
0 when already at maximum health and 1 after repair. The native equipment layer
checks ownership, research and presence, then pays resources (early shields) or
factory inventory (later shields). The original shield strengths and double-indexed health caps are retained.
For labs/factories the DOS routine indexes beyond the four-pointer table and
reads its caps from DS:0000. The native UI, like the original caller, only
permits repair below normal building health, so an oversized repair cannot
be applied repeatedly. AI can repair its tower too.


## Further strategy translations

Operations 41 and 42 implement the passage predicate (`11B9:1B40`) and
four-neighbour reachability (`0D24:39B1/3BA7`). Friendly/allied towers are
corridors. Neutral land is a corridor only with an active allied army and no
hostile army. Empty or hostile land is a terminal destination. The starting
sector bypasses that terminal stop. Aircraft classes 6–9 can cross gaps while
ground units remain at their origin. The 6502 traversal is iterative to bound
stack use; random worlds are compared with the DOS recursive traversal.

Operations 43/44 merge whole alliance groups (`16B4:3156`) and remove a
faction from its entire group (`0D24:3F9D`). The previous fixed truce expiry
has been removed. Negotiation acceptance is still a C64 policy.

Operations 45/46 translate atomic and partial equipment purchases
(`1A17:1383/12B4`). Both use existing inventory first, then early-design
resources. Atomic failures preserve inventory and stocks. Partial purchases
consume available inventory and as many directly made items as affordable.

Operations 47–50 translate personality-weighted economy plans, worker
allocation, weighted research/manufacturing goal selection and availability
scans (`16B4:18F7–2269`, `11B9:1262`, `0000:C54C`). Four original personality
tables remain private. Whole-sector results, plan bytes and RNG are compared
with DOS, including existing and newly selected goals. The native simulation
uses these routines through a leaf AI overlay; payments and rare-rule switches
occur only after the calling overlay has returned.

Operations 51/52 select and apply original AI turret upgrades and building
repair (`16B4:0A60/168A`). Random building/slot selection preserves nuclear
retaliators and prefers up to two nuclear defenders. Repair uses personality
thresholds and the original double-indexed health caps. Its observed batch
consumption quirk is retained: multiple shields can be consumed while the
single-shield repair routine is invoked once for that age. An absent facility
also halves the loop index before decrementing it, so some lower facilities
are skipped; that original branch behavior is preserved.

Deployment recovers all 24 faction-order permutations (`DS:1CDA`) and 27
computer population counts (`DS:1DC0`). Preparation chooses three orders per
epoch with the original random bound 24, includes the chosen human faction,
and selects computer land by random rejection sampling. Initial population
is selected men minus one, matching `CS0:126D/12C8`; the final battle uses
saved people divided by ten, then subtracts one. The current front end reserves
the human start before computer placement; the DOS alternating deployment UI
and remembered computer starts across island re-entry still need translation.
