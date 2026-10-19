# QA-rapport — v4.0.0

## Valideringsstatus (kjørt i byggemiljøet)

1. To-pass assembler bygger PRG `$0801–$491F` uten overlapp; build feiler hvis kode/tilstand når `$3700` eller PRG når `$C000`.
2. **114 automatiserte tester** (`dist/build_test_log.txt`): 43 arvede regeltester + IRQ-motor, rasterstolper, tittelbilde, joystick-akkorder, diplomati (inkl. 16-bit styrke, AI respekterer våpenhvile, brudd, utløp, lagring), oppfinnelser, `U`-stigen, disk (scratch, verify, skrivebeskyttet disk, enhetsnummer, v3-avvisning, READST-feil, skjerm av/på), minnekart, tilfeldig tastaturtest (fire frø × 260 hendelser) med invarianter, og bygg-/pakketester (reproduserbar PRG og ZIP).
3. **Mutasjonssjekk** (`tools/mutation_check.py`): 13 bevisste feil — AI ignorerer våpenhvile, angrep beholder våpenhvile, skjermen blir på under disk, rasterlinje-MSB lekker, snudd styrkesammenligning, 8-bits styrke, manglende IRQ-kvittering, ignorert READST, manglende scratch, ødelagt X etter rangoppgradering, feil `U`-rekkefølge, markørblink på, tikk-drift — alle fanget av testene.
4. D64-katalog, BAM og sektorkjede valideres mot PRG (bygges alltid på nytt i testen).
5. PNG-forhåndsvisninger rendres fra modellert C64-skjermminne, ikke fra VICE. Forhåndsvisningen fanget en feil testene ikke så (tittelfarger 8–15 → flerfargetegn).

## Feil funnet og rettet under v4-arbeidet

Hjelpelinjer 41 tegn (fanget av eksisterende plot-grensetest) · siste rasterstolpe ble overskrevet i samme avbrudd (test) · foreldet D64 validert (test) · tittelfarger (forhåndsvisning) · KERNAL-markørblink kunne XOR-e skjermminne (analyse) · `$D011`-MSB kunne lekke inn i rasterlinjen ved disk-blanking (mutasjon).

## IKKE testet

- VICE x64sc / ekte C64C: VIC-II-timing, rasterstolpenes utseende og jitter, badlines, sprite-DMA.
- SID 6581/8580 lyd og balanse mellom musikk og effekter.
- Ekte joystick og tastatur-/joystick-interferens.
- KERNAL serielinje mot ekte 1541 / SD2IEC / Ultimate, inkludert `S0:`-scratch og VERIFY.
- PAL/NTSC-tempo, spillbalanse over alle 28 øyer med menneskelig spill.

En `PASS` fra Python-6502-modellen er ikke maskinvareverifisering. Se `HARDWARE_TEST_PLAN.md`.
