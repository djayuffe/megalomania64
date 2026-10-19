# Mega-Lo-Mania 64 v2 — implementerte spillregler

## Kampanje

28 deterministiske øyer i 10 tidsaldre, tre øyer per alder 1–9 og én i alder 10. Hver øy bruker en 4 × 3-gridskjelett med 12 territorier, fem terrengtyper og egne innbakte mineralforekomster. Standard befolkning blir større i senere epoker. Tre AI-rivaler starter i adskilte sektorer (eier-ID 2, 3, 4). Spiller er ID 1, neutral ID 0. Fargeidentitet er separat fra logiske ID-er. Å vinne en øy krever alle 12 sektorer, tap skjer når spilleren har 0. Fullstendig kampanjeseier gis etter øy 28.

`L` + tosifret tall starter et checkpoint fra oppgitt øy og beregner reserve deterministisk. Dette er **ikke** lagring/gjenoppretting av levende spilltilstand. Etter seier økes kampanjereserven med 6, maksimalt 90.

## Ressursmodell

| Felt | Grenser | Regler |
|---|---|---|
| owner | 0–4 | Neutral/spiller/tre AI |
| people | 0–90 | Reserve, vekst og soldater |
| vein | 0–95 | Lokal, endelig mineralreserve |
| ore | 0–95 | Minedriftens lager; brukes til bygninger og våpen |
| miners / labs | 0–12 | Tildelte arbeidere på hver sektor |
| level | 0–5 | Teknologinivå; startnivå avhenger av epoken |
| research | 0–23 | Forskningspoeng; 24 poeng = ett nytt nivå |
| weapons | 0–90 | Materiell; både offensiv og defensiv effekt |
| fort | 0–9 | Lokalt fortifikasjonsnivå |
| buildings | bitmask 0–7 | Mine=1, lab=2, factory=4 |
| minegrade | 0–2 | Ekstra uttak pr. tick |
| policy | bitmask 0–3 | Bit0=automatisk våpen, bit1=automatisk fort |

Mineralproduksjon = `miners + minegrade` pr. tick, begrenset av `vein` og lagerkapasitet. Forskning = `labs` forskningspoeng pr. tick med lab, går videre én rang ved 24 poeng og bevarer restpoeng. Befolkning vokser hver 8. tick når det er arbeidsfri kapasitet, og små gjenlevende garnisoner kan komme tilbake. Samtlige ressurser oppdateres i samme deterministiske 6502-simulasjon.

Kostnader: mine-oppgradering 8; lab 6; fabrikk 10; våpen 4; fort 12. Automatisk våpen kjøres bare ved minst 16 ore og under 24 våpen, automatisk fort ved minst 24 ore og under fort 5. Hver politikk settes separat per sektor; erobring nullstiller politikken. AI bygger økonomi, produserer våpen og investerer ved overskudd også i mine og fort.

## Kamp og troppetransport

Alle operasjoner bruker ortogonal nærhet uten venstre/høyre-wrap. Angrep krever minst åtte innbyggere på avsenderbasen. Normal `X`: `force = people // 2`. Tung `T`: `force = people // 2 + (people // 2) // 2`. Antall mobiliserte våpen er `min(force, source_weapons)` og trekkes fra avsender. Kampsystemet bruker kun 8-bit beregninger som ikke når 256 innenfor lovlige verdier.

```text
offense = force + mobilized_weapons + 4 * tech
if heavy: offense += force // 2

defense = defender_people + 4 * fort + 4 * tech + (defender_weapons // 2)
```

Ved lik eller større offensiv styrke erobres sektoren og får en ny gruvecamp. Ved nederlag dør `force // 2` av forsvarerne (minimum én gjenlevende), én defensiv fortifikasjon og ett våpen ødelegges hvis tilgjengelig. Denne beleiringsslitasjen hindrer at maksimalt befestede territorier blir matematisk uinntagelige. Kapsler er 90 folk og 90 våpen.

`H` forsterker en tilstøtende *egen* sektor med opptil halve kildebefolkningen (uten å gå over målsektorens kapasitet 90) og maksimalt fire våpen. Bygninger, jobber, research, mineraler og fort blir bevart. Angrepskommandoer har eksplisitt vern mot å skyte på egne sektorer.

## Motstandere

Én rival-ID 2, 3 eller 4 får sin AI-handling per scheduling-event (runder over fraksjoner), med roterende kildesektor. Nøytrale sektorer kan tas først, deretter vurderes fiender (inkludert andre dataspillere) mot estimert full offensiv/defensiv styrke. Militære og økonomiske handlinger bruker de samme datastrukturene som spilleren. Dette er deterministiske heuristikker, ikke en optimal strategisøker.

## Grafikk og lyd

VIC bank 0, screen `$0400`, screen colours `$D800`; `$D018=$1E` velger skjerm `$0400` og 2 KB tegnsett `$3800`. Markørsprite ligger på `$3700` med pointer `$DC` på `$07F8`. Blandede hires/multicolor tegn gir både detaljert spilltekst og lavkost-øygrafikk. Fire 6×5 kystmasker blandes deterministisk med biome-koder og kampanjenummer. Det tegnes kun én sektor når bygning/befolkning endrer grafikken, ikke alt terreng hvert tick. Vannsprite/bitmap-buffere er ikke brukt. SID har to musikalske stemmer og én til handlingseffekter.

Oppdatering: 16 videoframes per strategitick PAL, 19 NTSC, valgt via KERNAL-flagg `$02A6`. Den faktiske hastigheten under ekte VIC badlines og KERNAL IRQ er ennå **ikke** maskinvaremålt.


## v3 technological doctrines

Per-sector doctrine is a 3-state cycle: industry=0 (level>=2 gives +2 ore per tick with miners), military=1 (+6 offensive power if level>=2), defense=2 (+8 defense power if level>=2). Research rank costs are `[24,32,40,48,56]` scientist-work points instead of a flat 24. The human can switch doctrine with Q, rivals use distinct initial sector roles; colonies inherit source doctrine on conquest.

## Live game save

See `SAVE_FORMAT.md`. Save and load on device 8 are modeled in opcode unit tests but need live hardware/VICE acceptance.


## v4 additions

**Diplomacy.** `truce[f]` (ticks left) and `truce_cool[f]` (ticks until talks) per faction id. Key `E` on a rival sector: refused if no rival is selected, if a truce is active, or while cooling down; otherwise compares 16-bit strengths `Σ people + weapons/2 + 4·level` and grants 90 ticks when the human's is ≥ the rival's, else imposes 60 ticks of cool-down. `ai_turn` never targets human sectors for a faction holding a truce. `player_attack` voids the target's truce (60 tick cool-down) only when the launch will really happen (source garrison ≥ 8) and the target is a rival. Expiry also starts the 60-tick cool-down. Truces are reset on every island and saved in snapshot v4.

**Inventions.** Ten signature weapons, one per epoch: CLUB, SPEAR, SWORD, BALLIS, XBOW, MUSKET, CANNON, TANK, MISSIL, LASER. HUD row 12 shows the current one. A human sector's rank-up prints `INVENTION: <NAME> MARK <rank>`. This is presentation only: combat maths is unchanged (tech still adds 4 per rank to offence and defence).

**Develop (`U`).** Priority ladder on the selected own sector, executed through the normal build routines: laboratory (6 ore) → factory (10) → miners up to 2 → mine upgrade (8) ×2 → scientists up to 2 → fort up to 3 (12) → weapons up to 30 (4) → miners up to 4 → fort up to 9. Does nothing (shows the normal denial) when nothing is affordable.

**Joystick.** See `README.md`: FIRE tap, eight FIRE+direction chords, context-sensitive tap on pause/victory/defeat.
