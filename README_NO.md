# Mega-Lo-Mania 64 v3.0 — norsk spillmanual

Uoffisielt, selvstendig utviklet strategispill inspirert av Mega-Lo-Mania for **Commodore 64 / C64C uten minneutvidelse**. Spillet benytter ekte 6510/8500-maskinkode, VIC-II tegnsett/grafikk, SID og fire konkurrerende fraksjoner.

## Oppstart

Monter `dist/MegaLoMania64.d64` på en 1541-kompatibel stasjon, eller autostart `dist/MegaLoMania64.prg` i VICE. På BASIC-prompten: `LOAD"MEGALOMANIA",8,1` og `RUN`.

## Spillet

28 øyer, ti epoker, 12 territorier per øy. Du konkurrerer med tre rivaler om gruver, befolkning, forskning, våpen og kontroll over hele øya. Bygg gruve, laboratorium og fabrikk. Skap styrker, ta territorier og trykk **C** etter seier for neste øy. Etter siste øy vises kampanjeseier.

## Taster

| Tast | Funksjon |
|---|---|
| W A S D | Flytt markøren mellom territoriene |
| ENTER | Velg din egen sektor som base for angrep og overføringer |
| X / T | Standard angrep / tungt angrep mot nabo |
| H | Overfør folk og våpen til et eget naboterritorium |
| M / J | Flere / færre gruvearbeidere |
| R / K | Flere / færre forskere (krever laboratorium) |
| B | Oppgrader gruven (8 malm) |
| V | Bygg laboratorium (6 malm) |
| G | Bygg fabrikk (10 malm) |
| P | Produser våpen (4 malm) |
| F | Bygg befestning (12 malm) |
| Y / Z | Automatisk våpenproduksjon / befestning |
| Q | Bytt lokal doktrine (I industri, M militær, D forsvar) |
| O | Lagre spilltilstand på stasjon 8 (`ML64SAVE`) |
| I | Laste inn sist lagrede spilltilstand fra stasjon 8 |
| SPACE | Pause og fortsett |
| C | Fortsett til neste øy etter seier |
| L + 01..28 | Start en øy fra starten (ikke ekte savegame) |
| N | Start kampanjen på nytt / avbryt øyvalg |

Port 2-joystick støtter markørbevegelse og standardangrep/valg av base.

## Teknologi og doktrine

Forskning krever 24, 32, 40, 48 og 56 forskningspoeng på stigende nivåer. Industri på nivå 2+ gir +2 malm per tick med aktive gruvearbeidere. Militær på nivå 2+ gir +6 i offensiv styrke. Forsvar på nivå 2+ gir +8 i defensiv styrke. Samme sektor kan skifte doktrine med Q.

## Lagring og tiltro

Programkode og regler er testet med 6502-opcode-tester. D64-struktur og bygg er verifisert. **VICE, SID, ekte joystick og den faktiske 1541-lagringen er ikke maskinvaretestet.** Lagring via `@`-erstatt er ikke pålitelig på alle historiske disketter/firmware: bruk reservekopi. Ikke anta at tilstanden er trygg uten test på din enhet.

## Bygg

`python3 tools/build.py --test` — krever Python 3.10+, ingen tredjepartsavhengigheter. `--preview` krever Pillow.

Dette er et nytt, kompakt strategispill basert på samme type spillmekanikk som Mega-Lo-Mania, ikke en 1:1-gjenskaping av de originale spillfilene.
