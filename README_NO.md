# Mega-Lo-Mania 64 v4.0 — norsk spillmanual

Uoffisielt, selvstendig utviklet strategispill inspirert av Mega-Lo-Mania for **Commodore 64 / C64C uten minneutvidelse**. Ekte 6510-maskinkode, VIC-II tegnsett og sprites, SID, rasterinterrupt-motor og fire konkurrerende fraksjoner.

## Oppstart

Monter `dist/MegaLoMania64.d64` på en 1541-kompatibel stasjon, eller autostart `dist/MegaLoMania64.prg` i VICE. På BASIC-prompten: `LOAD"MEGALOMANIA",8,1` og `RUN`. Trykk **FIRE eller en tast** på tittelbildet.

## Spillet

28 øyer, ti epoker, 12 territorier per øy. Du konkurrerer med tre rivaler om gruver, befolkning, forskning, våpen og kontroll. Bygg gruve, laboratorium og fabrikk, skap styrker, ta territorier og trykk **C** etter seier for neste øy. Etter siste øy vises kampanjeseier.

## Taster

| Tast | Funksjon |
|---|---|
| W A S D | Flytt markøren mellom territoriene |
| ENTER | Velg egen sektor som hærkilde (sprite 1 markerer den) |
| X / T | Standard angrep / tungt angrep mot nabo |
| H | Overfør folk og våpen til eget naboterritorium |
| M / J, R / K | Flere / færre gruvearbeidere, flere / færre forskere |
| B, V, G, P, F | Gruveoppgradering (8 malm), laboratorium (6), fabrikk (10), våpen (4), befestning (12) |
| Y / Z | Automatisk våpenproduksjon / befestning |
| Q | Bytt doktrine (I industri, M militær, D forsvar) |
| **E** | **Foreslå våpenhvile med eieren av valgt rivalsektor** |
| **U** | **Utvikle valgt egen sektor automatisk** |
| O / I | Lagre / laste `ML64SAVE` på oppstartsstasjonen (standard 8) |
| SPACE | Pause |
| 1 2 3 | Hastighet: sakte / normal / rask |
| C / N | Neste øy etter seier / ny kampanje |
| L + 01..28 | Start en øy fra starten (ikke ekte savegame) |

## Joystick (port 2)

| Handling | Resultat |
|---|---|
| Stikke | Flytt markør (ett steg per nytt retningstrykk) |
| FIRE-trykk | ENTER på egen sektor, ellers angrep · fortsett ved pause · neste øy ved seier · ny kampanje ved nederlag |
| FIRE holdt + opp | `T` tungt angrep |
| FIRE + ned | `U` utvikle |
| FIRE + venstre | `Q` doktrine |
| FIRE + høyre | `E` våpenhvile |
| FIRE + opp-venstre / opp-høyre | `H` overfør / `Y` autovåpen |
| FIRE + ned-venstre / ned-høyre | `Z` autofort / pause |

En akkord utløses når mønsteret har vært stabilt i 4 bilder; beveger du stikka mens FIRE holdes, avbrytes FIRE-trykket.

## Diplomati

Styrke = sum over fraksjonens sektorer av `folk + våpen/2 + 4·teknologi`. En rival godtar våpenhvile hvis **din styrke ≥ deres**, ellers avslår den og snakker ikke med deg på 60 tikk. Våpenhvilen varer 90 tikk; da angriper ikke denne rivalen deg (de andre kan fortsatt). Et ekte angrep (garnison ≥ 8) mot partneren bryter avtalen og gir 60 tikk karantene; angrep på ledig land bryter den aldri. Når en våpenhvile utløper starter også 60 tikk karantene.

## Oppfinnelser

Hver epoke har et signaturvåpen (kølle, spyd, sverd, ballista, armbrøst, musket, kanon, stridsvogn, missil, laser) som vises som `ARM:` i sidepanelet. Hver gang en av dine sektorer når et nytt forskningsnivå, meldes `INVENTION: <VÅPEN> MARK n`.

## Teknologi og doktrine

Forskning krever 24, 32, 40, 48 og 56 poeng. Industri på nivå 2+ gir +2 malm per tikk. Militær på nivå 2+ gir +6 angrepsstyrke. Forsvar på nivå 2+ gir +8 forsvar.

## Lagring

`O` skriver først en DOS `S0:`-scratch av gammel fil, deretter vanlig `SAVE`, og leser deretter filen tilbake med KERNAL **VERIFY**. Spillet melder «GAME SAVED AND VERIFIED» bare hvis begge deler går bra. Format v4 (inkluderer våpenhviler); v3-filer avvises. Skjermen er blank mens disken arbeider.

## Tiltro

Regler, IRQ-logikk, joystick, diplomati, disk-shim og D64-struktur er testet med 116 opcode-tester i en 6502-modell. **Kjørt i VICE 3.7.1 (PAL og NTSC, virtuell diskenhet):** oppstart, tittelbilde, kart, taster, angrep og lagring/innlasting. **Ikke testet:** SID-lyd, ekte joystick, maskinvarenivå 1541 og ekte C64C. Bruk `docs/HARDWARE_TEST_PLAN.md`, og lagre kun på en **kopi** av disketten til dette er gjort.

## Bygg

`python3 tools/build.py --test` — Python 3.10+, ingen tredjepartsavhengigheter. `--preview` krever Pillow, `--package` lager release-ZIP.

Dette er et selvstendig strategispill i samme sjanger som Mega-Lo-Mania, ikke en 1:1-gjenskaping.
