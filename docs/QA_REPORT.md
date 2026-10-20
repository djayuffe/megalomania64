# v5.0.0-dev audio/colour validation — 20 October 2026

- Final PRG: `$0801–$BEE9`, 46827 bytes including load address; 278 bytes below `$C000`.
- **228 automated tests passed** (`dist/build_test_log.txt`). This includes the four-part sequencer, voice-one effect ownership/recovery, volume changes, decaying percussion, full effect RAM crossing, partial-file fallback, SID detection/DC boost cleanup, nested NMI while I/O is banked out, neutral grey mapping and mixed story raster/serial ordering.
- **16 focused mutation checks passed** (`tools/mutation_streaming.py`). The historical v4 45-mutant suite was not rerun; these counts are not added together.
- Final VICE 3.9 x64sc runs: **PAL/8580 and NTSC/6581**, true 1541 drive emulation, virtual-device traps disabled. Both traverse all 20 original picture scenes, verify title/game score bytes, island-card sprites, full effect banks and resident speech against the full disk, and complete low-RAM and KERNAL-shadow voice clips at exact expected pointers.
- SID revision detection selects the expected one-DC-source 6581 / three-source 8580 digi gain. Timed full-orchestra and original-speech playback completes on both models.
- Four normal-speed mono 16-bit WAV captures per model contain non-silent PCM: title music, game music, full orchestra effect and original speech. **No 16-bit digital clipping** was measured. Detailed duration, RMS and peak values are in `dist/validation_v5.json`; signal-level verification is not a human listening test.
- Final evidence is local in `../recovery/vice/av_pal_8580_percussion` and `../recovery/vice/av_ntsc_6581_percussion`: screenshots, RAM dumps, monitor transcript, WAV files and `audio_metrics.json`. Earlier recorder attempts produced empty files and are excluded from the final evidence bundle.
- A fresh assembly matches the final PRG byte-for-byte. The standard fallback disk remains self-contained. The normal build and non-image regression tests also run without optional Pillow/NumPy; colour conversion tests require those libraries and CI installs them.

VICE exposed that KERNAL serial reads can delay raster splits. Story panels now hold without background serial reads and blank while their successor loads; screenshots confirm readable hires text below multicolour art. A static EXE probe also establishes the SUNRISE→MUNRISE filename rewrite and the actual six-bit sunrise palette copy.

Original game rules/terrain/balance and exact original scrolling/timing remain unfinished. Music retains all four parts through a three-oscillator SID arrangement, with quantized dynamics and different timbres. No physical C64/drive, human listening judgment or complete campaign playtest is claimed.

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
