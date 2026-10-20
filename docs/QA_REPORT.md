# v5.0.0-dev validation — 20 October 2026

- Final build: `$0801–$BF27`, 46889 PRG bytes including load address, 216 bytes below `$C000`.
- **211 automated tests passed**; full output in `dist/build_test_log.txt`.
- **9 focused streaming/music mutation checks passed** (`tools/mutation_streaming.py`). The historical 45-mutant v4 suite was not rerun for this build.
- VICE 3.9 x64sc, PAL and NTSC, true 1541 drive emulation with virtual-device traps disabled: all 20 streamed scenes reached the restored native title; the original-score bank matched disk bytes; island-card sprites and resident speech matched their disk payloads; both a low-RAM voice and a voice crossing into RAM under KERNAL finished at their exact expected addresses.
- NTSC sprite DMA exposed nested sample NMI reentry and a final-counter underflow. A reentry guard fixes this; a model regression injects the nested interrupt at the final sample. Both final VICE runs include this fix.
- Local VICE evidence: `../recovery/vice/pal_guarded` and `../recovery/vice/ntsc_guarded`. These contain screenshots, monitor transcripts and RAM captures. `dist/validation_v5.json` records artifact hashes and scope.
- The distributed default D64 exercises the optional-content fallback. Original-derived scene, speech, music and island files are generated locally by the documented recovery commands into a separate full D64; they are not embedded in the public source archive.

Remaining limits: original game rules and exact scrolling/timing have not been reconstructed; SID music is a three-voice arrangement with approximate timbres and one omitted MOD channel. The final VICE runs disable audio and establish execution/memory behavior, not listening quality. No physical C64, real drive, SID listening or human campaign playtest is claimed. This is a development build.

The v4 report below is historical and describes its own older build and emulator coverage.

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
