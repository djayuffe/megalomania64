# Endringslogg

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
