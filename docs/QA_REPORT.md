# v5.0.0-dev scrolling intro validation — 20 October 2026

- Final PRG: `$0801–$BF96`, 47000 bytes including load address; 105 bytes below `$C000`.
- **233 automated tests passed** (`dist/build_test_log.txt`). New tests cover every credit offset through 390 pixels, page crossings, fixed logo memory, raster setup, oversized-card rejection, 70 logical ticks per PAL/NTSC second and story patches preserving artwork. Existing music/effects/speech/game tests still pass.
- **20 focused mutation checks passed** (`tools/mutation_streaming.py`). The historical v4 45-mutant suite was not rerun; counts are not combined.
- VICE 3.9 x64sc on **PAL/8580 and NTSC/6581**, true 1541 emulation with virtual-device traps disabled, traverses all 29 original intro stages and reaches the fan game. The complete 320×40 logo region is pixel-identical across all eight fine-scroll positions on both models. Credit charset/logo, title/game score, effect and speech RAM bytes match the disk.
- Eight fresh mono 16-bit WAVs verify non-silent title/game music, the full orchestra effect and original speech. No measured digital clipping; metrics are in `dist/validation_v5.json`. This is signal-level verification, not a human listening judgment.
- Exact low-RAM and KERNAL-shadow speech completion pointers, island-card sprite setup and SID revision detection pass on both models.
- Final local evidence: `../recovery/vice/scroll_pal_audio_final`, `scroll_ntsc_final`, and the context-preserving `scroll_ntsc_release` harness run. Earlier diagnostic failures are excluded from the delivery bundle.
- The standard source disk remains self-contained without original content. The private full disk contains 62 content files plus the PRG. The launcher defaults to turbo floppy; validation above uses true drive.

Two hardware-specific failures were corrected: speech overwrote an intro-only disk callback, and VIC badline stalls delayed the credit/logo split. Polling now stays resident; an early raster IRQ waits for the split line and chooses a logo placement for the current row counter. The original sprite-source RAM remains intact.

Story order, text-strip coordinates, 250-retrace intervals, complete credit canvases and scroll distances are established from the executable. Nominal 70 Hz source motion is adapted to 50/60 Hz displays; exact VGA presentation, palette fades and original disk-load pauses are not claimed. The native title/parade and the fan strategy engine remain. Original campaign rules/maps/UI/balance, physical hardware and a complete campaign playtest are unfinished.

The following v4 report is historical.

---

# QA-rapport — v4.4.0

## Valideringsstatus (kjørt i byggemiljøet)

1. To-pass assembler bygger PRG `$0801–$B51B` uten overlapp; build feiler hvis kode/tilstand når `$3200` (spriterammen for originalsprites) eller PRG når `$C000`.
2. **177 automatiserte tester** (`dist/build_test_log.txt`): 43 arvede regeltester + IRQ-motor, rasterstolper, tittelbilde, joystick-akkorder, diplomati (inkl. 16-bit styrke, AI respekterer våpenhvile, brudd, utløp, lagring), oppfinnelser, `U`-stigen, disk (scratch, verify, skrivebeskyttet disk, enhetsnummer, v3-avvisning, READST-feil, skjerm av/på), minnekart, tilfeldig tastaturtest (fire frø × 260 hendelser) med invarianter, og bygg-/pakketester (reproduserbar PRG og ZIP).
3. **Mutasjonssjekk** (`tools/mutation_check.py`): 45 bevisste feil (v4.4: lydspiller, NMI uten CIA-flagg, ikke-dempede stemmer, sample-prioritet, intro-avsløring, overskytende soldat, manglende gjenoppretting av sprite-registre m.fl.) — AI ignorerer våpenhvile, angrep beholder våpenhvile, skjermen blir på under disk, rasterlinje-MSB lekker, snudd styrkesammenligning, 8-bits styrke, manglende IRQ-kvittering, ignorert READST, manglende scratch, ødelagt X etter rangoppgradering, feil `U`-rekkefølge, markørblink på, tikk-drift, marsj mister fortegn, ikon før hæren er framme, bygningsikon feil epoke, hærsprite skjules aldri — alle fanget av testene.
4. D64-katalog, BAM og sektorkjede valideres mot PRG (bygges alltid på nytt i testen).
5. PNG-forhåndsvisninger i `dist/preview_*.png` rendres fra modellert C64-skjermminne; ekte VICE-bilder ligger i `dist/vice/`. Forhåndsvisningen fanget en feil testene ikke så (tittelfarger 8–15 → flerfargetegn).

## Kjørt i VICE 3.7.1 x64sc (v4.1, headless, PAL og NTSC)

- D64 autostarter (virtuell enhet 8 / KERNAL-traps — **ikke** maskinvarenivå 1541-emulering).
- Tittelbilde med rasterstolper og fargesyklet logo rendres på PAL og NTSC. VICE avslørte at stolpene lå over to undertekstlinjer og gjorde dem uleselige; stolpene har nå eget bånd øverst og teksten er flyttet ned (`tools/vice_smoke.sh`, bilder i `dist/vice/`).
- Kartet, HUD, markørsprite og kildemarkør rendres; tastatur (flytt, base, angrep, bygg, hastighetstaster, ny runde) fungerer; angrep erobrer fri sektor (kontrollert mot minnet via VICE-monitor).
- `O` skriver `ML64SAVE` (1 blokk) til D64 (lest tilbake med `c1541`); `I` gjenoppretter tilstanden (tikk og folketall endres tilbake).
- v4.2: introbilde (bitmap, bank 1) vist på PAL og NTSC; HUD-farger sjekket visuelt (fanget flerfargeteknings-feilen); lydopptak fra VICE (WAV) viser titteltonene 98/392/587 Hz. Lydeffektene er kun modell-testet (registre, prioritet, sveip, gate) — ingen har lyttet.
- v4.4 (PAL): intro (avsløring fra midten, parade med åtte soldater, rasterstolper etter paraden, PRESS FIRE-syklus) sett i skjermbilder; WAV-opptak fra VICE viser lydbrudd i avsløring/parade og så tittelmelodien; etter introen fungerer kartet, marsj og erobring, og spillets sprite-registre er gjenopprettet. NMI-spilleren spilte en hel eksplosjonslyd og stoppet (pekeren lest via monitoren). Kun modell- og skjermbildekontroll av lydkvalitet — ingen har lyttet, ingen NTSC-kjøring av v4.4.
- Rebalansering (AI 16/8 tikk i stedet for 8/4, 25 % angrepsmargin): kun målt med skriptede spillere i modellen. Ingen menneskelig spilltest.

## Feil funnet og rettet under v4-arbeidet

Hjelpelinjer 41 tegn (fanget av eksisterende plot-grensetest) · siste rasterstolpe ble overskrevet i samme avbrudd (test) · foreldet D64 validert (test) · tittelfarger (forhåndsvisning) · KERNAL-markørblink kunne XOR-e skjermminne (analyse) · `$D011`-MSB kunne lekke inn i rasterlinjen ved disk-blanking (mutasjon).

## IKKE testet

- Ekte C64C: VIC-II-timing, rasterstolpenes jitter, badlines, sprite-DMA (VICE viser kun utseende).
- SID 6581/8580 lyd og balanse mellom musikk og effekter.
- Ekte joystick og tastatur-/joystick-interferens.
- KERNAL serielinje mot ekte 1541 / SD2IEC / Ultimate og VICE med ekte 1541-emulering (kun virtuell enhet er kjørt).
- Spillbalanse over alle 28 øyer med menneskelig spill.

En `PASS` fra Python-6502-modellen er ikke maskinvareverifisering. Se `HARDWARE_TEST_PLAN.md`.
