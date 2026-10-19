# Endringslogg

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
