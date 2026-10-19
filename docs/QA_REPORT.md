# QA-rapport — v3.0.0

## Valideringsstatus

1. To-pass assembler bygger faktisk C64 PRG uten overlapp. Program-/datasymboler slutter før spriteområdet `$3700`; spriteområdet er `$3700`, tegnsettet `$3800` til `$3FFF`.
2. 43 automatiserte native-opcode-tester, inkludert 28 kampanjeetapper, slag/beleiring, tre rivaler, joystick-logikk, grenseverdier, teknologi, nye doktriner, ny AI-bemanning, disk snapshot/restore med modellert KERNAL, tilsiktede korrupsjonsfeil og PAL/NTSC-skalering. Se `dist/build_test_log.txt`.
3. D64-filens katalog, BAM og faktisk PRG-sektorkjede valideres mot binærfilen.
4. GIF/PNG forhåndsvisninger tegnes fra modellert C64-skjerm- og tegnsettminne, ikke fra ekstern VIC-II-emulator.
5. ZIP bygges ut fra kildekode og verifiseres i ren arbeidsmappe; signaturfil følger med.

## Begrensning — IKKE testet

- VICE x64sc-kjøring, PAL/NTSC-rasterprofilering, oppsett på ekte Commodore 64C, SID 6581/8580 audio, fysisk joystick og KERNAL `SAVE`/`LOAD` mot ekte 1541/SD2IEC.
- Reell menneskelig kampanje på 28 øyer, spillbalanse og eksakt originalparitet.
- DOS-replace-syntaks for alle stasjoner. Sjekk lagring/innlasting på en kopi før du stoler på progresjonen.

En `PASS` fra Python 6502-interpreter er ikke det samme som verifisert maskinvarekompatibilitet. Se `HARDWARE_TEST_PLAN.md` for gjenstående akseptanse.
