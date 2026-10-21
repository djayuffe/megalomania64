# Endringslogg

## Native gameplay integration (21 October 2026)

- Original battle scheduler, facility damage, tower loss, defence recall and
  ordinary nuclear detonation translated; 5,115 scenarios compared with DOS
  on host C and native 6502, plus all 448 campaign-sector initializations.
- Playable native economy, armies/capture, defences, nuclear retaliation and
  interception, four factions, AI difficulty, hotseat, diplomacy, victory,
  defeat and 28-island progression. Air units cross disconnected land groups.
- Two rotating CRC-checked saves, verified writes, newest-valid selection,
  bounded loading and RAM rollback; disk waits excluded from simulation time.
- Compressed code beneath I/O/KERNAL, rare-rule/audio cache sharing, safe native
  IRQ/NMI mapping and hardware wrappers. Fixed SID writes corrupting code RAM.
- AI, travel, starting allocation and interface are C64 adaptations. Special DOS
  future-shutdown branches and human campaign balance remain unverified.
  Original content and generated native D81 remain private.

## v5 recovered intro scrolling (20 October 2026)

- Original DOS story order and 14 text-strip stages, with recovered 250-retrace
  intervals; 15 complete 320x600 credit cards scroll over a 160-pixel viewport.
- Executable-checked card distances, fixed 40-pixel logo, and a nominal 70 Hz
  source clock adapted to PAL/NTSC. No center cropping or arbitrary card holds.
- Story-strip deltas keep 62 content files and the PRG on one D64. Resident
  polling survives speech overwriting intro RAM. Turbo floppy is the launcher
  default; set VICE_TURBO_FLOPPY=0 for true-drive playback.
- Original campaign rules/maps, palette fades, exact VGA frame timing and the
  original game UI remain unfinished. The playable strategy engine is the fan port.

## v5 audio/colour follow-up (20 October 2026)

- All four MOD parts retained using a shared-voice SID arpeggio; 16-level dynamics,
  correct ProTracker slide priority, decaying percussion, separate title/game banks, and complete SID
  state restoration after effects. Streamed intro holds now have music.
- Optional full-length original effect bank, exact crossing into hidden I/O RAM,
  8580 digi DC boost, and effects followed by queued spoken reactions.
- Perceptual per-cell palette optimization, neutral greys, and multicolour story
  artwork with hires lettering. Serial reads occur between split-mode story holds.
- Hidden RAM under I/O is represented separately in the CPU model and verified
  against VICE RAM captures. Original rules and scrolling are still unfinished.

## v5.0.0-dev (20. oktober 2026, lokalt arbeid)

- Ny, avgrenset LZHUF-dekoder; alle 101 DOS-ressurser behandlet. 85 IFF-filer
  validerer strukturelt (27 ILBM, 20 PBM, 38 8SVX); 16 øvrige ressurser er rådata.
- Amiga-disk: 510 byte data + 2 byte footer per sektor. 21 ILBM, 20 8SVX og
  to MOD-filer gjenfunnet; én ugyldig IFF avvist. Effektene regenerert uten footere.
- `war14` og `choose3` arrangert for tre SID-stemmer; hastighet/pattern-breaks
  bevart, sample-klang og volumfades tilnærmet, én kanal utelatt (1888 byte i RAM).
- Full D64 med 20 originale bildescener, dobbel VIC-buffer, originaltittel gjenopprettet
  før den innebygde tittelen, åtte resident lagrede stemmer og 28 øybilder fra disk.
- 6502-laster med kontroll av filformat, EOF, avkortede pakker og utdataområder.
- Talebanken bruker 4 bit / 4 kHz og leser RAM under KERNAL kun under sample-hentingen.
  Våpenhvile spiller spørsmål med køet svar.
- VICE fant at GETIN leste diskkanalen under CHKIN. Tastaturpolling bytter nå kanal;
  modellen og en regresjonstest gjenskaper den faktiske KERNAL-oppførselen.
- NTSC sprite-DMA kunne gi nestede sample-NMI og underløp ved siste sample;
  reentransvakt og regresjonstest hindrer dette. PAL og NTSC kontrollert i VICE.
- Eksakt original timing, bevegelse, musikk og spillregler er fortsatt ikke rekonstruert.
  Ingen påstand om identisk originalport eller ferdig v5-utgivelse.

## v4.4.0 (19. oktober 2026)

Originale Amiga-lydeffekter og en ny flerscene-intro bygget av de dekodede originaldataene.

- **Originale lydeffekter:** 11 Amiga-8SVX-effekter (stokk, kast, muskett, maskingevær, kanon, rakett, laser, eksplosjon, grynt, orkesterslag, pauker) er nedkonvertert til 4 bit / 5 kHz (`tools/orig_convert.py`, 8401 byte) og spilles via SID-hovedvolumet (`$D418`) av en NMI-spiller (CIA 2 timer A, latch 196 PAL / 203 NTSC, `src/sample.asm`). SID-stemmene dempes og musikken står stille mens en lyd spilles; `disk_begin` stopper spilleren (seriebussen er tidskritisk).
- **Hendelser:** angrep spiller epokens våpen (stokk, stokk, kast, kast, muskett, muskett, maskingevær, kanon, rakett, laser), erobring = eksplosjon, tapt sektor = grynt, avvist angrep = muskett, seier = orkesterslag, nederlag = pauker. Prioritet som for SID-effektene; øvrige effekter (valg, feil, oppfinnelse, våpenhvile, bygg, disk, tikk) er uendret på SID.
- **Ny intro (`src/title.asm`):** (1) galaksen åpnes rad for rad fra midten, 4 bilder per steg, med originalt orkesterslag; (2) åtte originale soldater (epoke 0–7 fra `ARMIES.LBM`) marsjerer inn fra venstre til hver sin plass og hilser med epokens våpenlyd; (3) rasterstolper bak logoen, tittelmelodi og PRESS FIRE. Tast eller FIRE hopper over når som helst; spillets sprite-registre lagres og gjenopprettes.
- **Minne:** motoren flyttet til `$8000` (kode og tabeller opp til `$9447`), lydbanken `$9447–$B517` (`$A000–$BFFF` er RAM fordi BASIC kobles ut, `$01=$36`); spriteramme og introskjerm-kilde i VIC-bank 1 (`$4000`, `$4D00`). Se `docs/MEMORY_MAP.md`.
- **Feil funnet av nye tester/VICE og rettet før utgivelse:** den selvmodifiserende `lda` i spilleren ble satt sammen som null-side-instruksjon og overskrev egen kode (modelltest); `fx_tick` og `orig_tick` kjørte under introen og overstyrte soldat-spritene (modelltest).
- **Tester:** 177 (nye: lydspiller, NMI-inngang, hendelses-samples, intro-avsløring, parade, hopp-over/gjenoppretting, 6502-modellen støtter nå RTI), 45 mutanter (22 nye).
- **Verifisert i VICE 3.7.1 (PAL):** introen vises (avsløring, parade, stolper, PRESS FIRE-syklus; skjermbilder), lydopptak fra VICE viser lydbrudd under avsløring/parade og deretter tittelmelodien, og spillet fungerer etter introen (marsj, erobring, sprites gjenopprettet); NMI-spilleren kjørte en hel eksplosjonslyd til slutt og stoppet (lest fra minnet via VICE-monitoren). **Ingen har lyttet** til lydene eller vurdert kvaliteten (4 bit / 5 kHz), og ingenting er prøvd på ekte maskinvare.
- **Ikke gjenvunnet:** den originale introsekvensen (Amiga-ILBM-bildene er fragmenterte, DOS-`.DAT`-filene er udekodet) og Amiga-musikken. Introen er en ny sekvens av originale ressurser. Valget av lyd per hendelse og soldat per epoke er dette prosjektets.

## v4.3.0 (19. oktober 2026)

Originaldata (PC-utgaven fra 1991, via reverse-engineering-pakke v11) pakket ut og nedkonvertert til C64. Se `docs/ORIGINAL_DATA.md`.

- **Introbilde = originalens galakse** (`MTARFLD.LBM`) omsamplet til 160x200 flerfarge bitmap (svart/blå/lyseblå/cyan/hvit, dither, maks. 3 farger per celle) under logoen.
- **Marsjerende hær:** angrep sender en original soldat (`ARMIES.LBM`, én rad per epoke, 4 gangbilder, flerfarge-sprite 2 i dobbel størrelse) fra kilde- til målsektor på 32 bilder i angriperens farge.
- **Erobringsikon:** erobret sektor viser en original bygning (`BUILDS.LBM`, sprite 3) i eierens farge når hæren er framme, deretter blinker den ut.
- **Originale øynavn** fra `MEGA.EXE`: ALOHA … ZAPPA, MEGALOMANIA, THE MOTHER.
- **Verktøy:** `tools/orig_import.py` (ILBM-leser, EXE-tekst), `tools/orig_convert.py --orig <mappe>`. Originalfilene ligger ikke i repoet (`original/` er ignorert).
- **Minne:** spriterammen `$3200–$33FF` (byggesjekk: kode/tilstand må holde seg under `$3200`, 91 byte margin), spritedata for alle epoker i `$7F40–$8BBF`, kopieres til bank 0 ved epokeskifte.
- **Tester:** 149 (14 nye: marsj i alle retninger, ikon-timing, epoke-kopiering, ILBM-leser, øynavn), 23 mutanter (4 nye).
- **Ikke gjenvunnet:** de 54 proprietære `.DAT`-filene (kart, teknologitre, balanse, tale, musikk). Radvalget soldat/bygning per epoke er dette prosjektets valg.
- **Verifisert i VICE:** introbilde, marsjerende hær og erobringsikon (skjermbilder). **Ikke** på ekte maskinvare.

## v4.2.0 (19. oktober 2026)

- **Introbilde:** 160x200 flerfarge bitmap (solnedgang, vulkan, slott, skip, logo) i VIC-bank 1 (`$4000–$7FFF`). Rasterstolpene går bak logoen (svart bakgrunn), og PRESS FIRE farge-syklerer via fargeminnet. Bildet genereres av `tools/make_intro.py`.
- **Lydeffekter:** 13 tabelldrevne effekter på SID-stemme 1 (prioritet, tonehøyde-sveip, gate-retrigging): valg, feil, angrep, erobring, tapt sektor, oppfinnelse, våpenhvile, bygg, disk, markørtikk, avvist, seier, nederlag.
- **Musikk:** pulsstemme med PWM + sagtann-bass, noter gates på nytt per steg; to nye melodier (seier, nederlag) via `music_over`.
- **Effekter:** kantblink (erobring, tap, oppfinnelse, seier), skjermskaking ved angrep, pulserende markør- og kildefarger, egen rammefarge per epoke.
- **HUD-farger:** fraksjonsfarget eier-rad, farget poenglinje, sidefelt og hjelpelinjer (kun hires-farger 0–7).
- **Feil funnet av nye tester/VICE og rettet før utgivelse:** `set_border` ødela Y i `load_island`; HUD-farger 8–15 ga flerfargetegn.
- **Verktøy/tester:** 135 tester (nye: lyd, effekter, HUD, introdata). Byggesjekk: motorkoden må holde seg under `$5800`.
- **Verifisert i VICE:** introbildet på PAL og NTSC; lydopptak fra VICE viser titteltonene (98/392/587 Hz). **Ikke** lyttet til effektene.

## v4.1.0 (19. oktober 2026)

Første utgivelse kontrollert i ekte emulator (VICE 3.7.1 x64sc, PAL og NTSC, virtuell diskenhet).

- **Tittelbilde:** rasterstolpene lå oppå undertekstene og gjorde dem uleselige (oppdaget i VICE). Stolpene går nå i eget bånd øverst (linje 55–118); teksten er flyttet til rad 11–23.
- **Hastighet:** taster `1`/`2`/`3` (sakte/normal/rask) med visning `SPEED n` øverst til høyre. Standard er nå normal (24 bilder PAL / 29 NTSC ≈ 0,48 s per tikk; før 0,32 s).
- **AI-balanse:** AI flytter hver 16. tikk (hver 8. fra epoke 5; før 8/4) og angriper bare med 25 % margin over forsvaret. Skriptede spillere i modellen overlever og kan vinne; uten tiltak ble selv en fornuftig spiller utslettet innen ca. 250 tikk.
- **Verktøy:** `tools/vice_smoke.sh` (headless VICE-oppstart, skjermbilder i `dist/vice/`).
- **Tester:** 116 (nye: hastighetstaster, AI-takt, AI-margin). Eksisterende tester justert for ny standardhastighet og ny tittel-layout.
- **Fortsatt ikke verifisert:** SID-lyd, ekte joystick, maskinvarenivå 1541, ekte C64C, menneskelig balansetest.

## v4.0.0 (19. oktober 2026)

**Motor**
- Rasterinterrupt-motor: én IRQ per bilde (CIA-timer-IRQ av) som kjeder til KERNAL (`$EA31`). Hovedløkken sover på `vblank` i stedet for å polle `$D012`; tikk-klokken akkumulerer forløpte bilder og beholder restbilder (ingen drift), og klemmer etter lange diskoperasjoner (maks. 8 bilder).
- Joystick port 2 samples i IRQ med kolonnene avvalgt (`$DC00=$FF`) før tastaturskanning.
- SID-musikk og lydeffekter kjører fra IRQ. Fire melodier (antikk, middelalder, industri, tittel) velges etter epoke.
- Tittelbilde med fargesyklet logo og kjedet rasterstolpe-stabel (16 stolper, 3 linjer, svingende startlinje). Siste stolpe vises nå full høyde (eget gjenopprettings-IRQ).
- Hardware-sprite 1 markerer hærkilde-sektoren.

**Spill**
- Diplomati: `E` foreslår våpenhvile med eieren av valgt rivalsektor. Aksept hvis din styrke ≥ rivalens (folk + våpen/2 + 4·teknologi, 16-bit). Varighet 90 tikk; avslag, brudd og utløp gir 60 tikk karantene. AI angriper ikke spilleren under våpenhvile; ekte angrep (garnison ≥ 8) mot partneren opphever avtalen.
- Oppfinnelser: hver epoke har et signaturvåpen på HUD (`ARM:`); hvert forskningsnivå for spillerens sektorer melder `INVENTION: <VÅPEN> MARK n`.
- `U` utvikler valgt sektor automatisk (laboratorium → fabrikk → gruvearbeidere → gruve → forskere → fort → våpen → …) via de vanlige byggerutinene.
- Joystick: FIRE-trykk + åtte FIRE+retning-akkorder (T, U, Q, E, H, Y, Z, pause) med 4 bilders debounce; FIRE er kontekstavhengig ved pause, seier og nederlag.
- Ny HUD-linje `PACT:` og `ARM:`; hjelpelinjer oppdatert.

**Disk**
- Lagring: DOS `S0:ML64SAVE` (scratch) over kommandokanal 15, deretter vanlig `SAVE` (ingen upålitelig `@0:`), deretter KERNAL **VERIFY**-tilbakelesing og `READST`-kontroll. Innlasting kontrollerer også `READST`.
- Enhetsnummer følger `$BA` (stasjonen spillet ble startet fra), ellers 8.
- Skjerm og sprites slås av rundt all serielinjeaktivitet (badline-/sprite-DMA); `$D011`-MSB røres aldri; avbrudd slås på igjen også etter feil.
- Snapshot-format **v4** (inkluderer våpenhviler). v3-filer avvises.

**Rettelser**
- KERNAL-markørblink (`$CC`) kunne XOR-e skjermminnet — slått av.
- KERNAL-meldinger (`$9D`) slått av så «SAVING»/«SEARCHING» ikke havner over kartet; gamle tastetrykk i tastaturkøen forkastes ved tittelbildet.
- Hjelpelinjer var 41 tegn og brøt over kanten (fanget av test).
- Tittelfarger 8–15 ga flerfargetegn og ødela teksten (fanget i forhåndsvisning).
- `D64`-testen validerte en foreldet fil; bygger nå alltid på nytt.

**Test og bygg**
- Testmodellen får IRQ-avfyring, KERNAL-diskshim (OPEN/CLOSE/SAVE/LOAD/VERIFY/READST), joystick-pinner, rasterlinje-MSB. 43 → 114 tester, mutasjonssjekket (13 bevisste feil, alle fanget).
- `tools/gen_tables.py`, `tools/make_sprites.py`, `tools/package.py` (reproduserbar ZIP), `Makefile`, GitHub Actions CI.

**Fortsatt ikke verifisert:** ekte VICE/maskinvare for VIC-II, SID, CIA, 1541, rasterstolpenes utseende og PAL/NTSC-tempo. Se `docs/HARDWARE_TEST_PLAN.md`.

## v3.0.0 (19. oktober 2026)

- Implementert lagring/gjenoppretting av levende spilltilstand ved C64 KERNAL SAVE/LOAD på logisk enhet 8, med versjonert filformat `ML64` v3, lengde og to 8-bits sjekksummer, kontroll av eier- og ressursgrenser, samt rekonstruksjon av epokegrafikk. Dette er verifisert med en modellert KERNAL-disk-shim, **ikke** VICE eller fysisk 1541.
- Avverger utilsiktet lasting på filens headeradresse med sekundæradresse 0; loader leser alltid til `$C000`.
- Ny lokalt styrt doktrine: industri, militær og forsvar. Ingen fiendesektor kan velges for spillerens doktrine.
- Forskningstid skalerer fra 24 til 56 poeng per teknologirang; industri øker gruveeffekt, militærdoktrine øker angrepsstyrke og forsvarsdoktrine øker befestet motstand.
- Rivalenes kolonier øker antall arbeidere dynamisk etter som ledig befolkning tillater det.
- HUD viser epokenavn og lokal doktrine; underliggende VIC-II grafikk beholder 2 KB tegnsett og delvis opptegning.
- Utvidet regresjonstesting fra 33 til 43 tester: save/load, korrupsjonsavvisning, PAL/NTSC ved innlasting, industri og forskning, automatisert arbeidsfordeling.
- Oppdatert begge manualer, arkitektur, formatspesifikasjon og QA; maskinvareavhengige begrensninger eksplisitt dokumentert.

## v2.0.0

- Fire konkurrerende fraksjoner, beleiring, tungt angrep, venneoverføringer, automatisk produksjon og forbedret kystgeografi.

## v1.0.0

- 28 øy-etapper, ti epoker, bygg, økonomi, forskning, kampanje, joystick og to SID-musikkstemmer.
