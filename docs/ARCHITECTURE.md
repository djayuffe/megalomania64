# v2.0 teknisk arkitektur for VIC-II / 6510

## Minnekart

| Adresse | Bruk |
|---|---|
| `$0801–$080C` | BASIC-kjede, linje `10 SYS4096` |
| `$1000–$2CBA` (omtrent) | Maskinkode, musikkdata, 28 verdenskart, datastrukturer, live spilltilstand. Nøyaktig sluttadresse må leses fra `dist/symbols.txt`. |
| `$3700–$373F` | Justert 64-byte markørsprite, `$07F8=$DC` |
| `$3800–$3FFF` | 256 glyphs × 8 byte = 2048-byte karaktersett |
| `$0400–$07E7` | 40×25 synlig tegnskjerm |
| `$07F8` | Sprite-0-peker |
| `$D800–$DBE7` | Colour RAM (bare lav nibble) |
| `$D400...` | SID registre for stemme 1/2/3 |
| `$FB–$FE` | Arbeidspekere for skriving i skjerm/Color RAM |

Programmet starter ved `$1000` uten RAM-utvidelse og er lastet inn via standard PRG-lasteadresse. PRG inkluderer hull frem til grafikken med nullutfylling. Build-systemet sjekker kodens slutt før sprites på `$3700` og bekrefter 2 KB font / 64-byte sprite. Kjørbar fil er omkring 14 KB, inkludert hull og BASIC-entry. Ingen ROM-hacks eller raster-avbruddsrutiner.

## Tegnsystem

`$D018=$1E`: VIC bank 0; skjerm ved `$0400`, custom glyphs ved `$3800`. `$D016=$18`: 40 kolonner og tegn-multicolor. For tegn med Color RAM-verdier 8–15 brukes 4 tobits-piksler pr. grafikkbyte og vertikal 8x multiplikasjon; for tekst med Color RAM 0–7 brukes 8 individuelle piksler. Land har 5 biomer, ekstra nyansesymboler, epoke-bygg, tårn og havmønster; tegnsystemet tegner separate 6×5-ruters sektorer i fire formmasker.

Den dyre operasjonen `clear_screen` utføres bare ved innlasting av ny øy. Under spill endres territorier selektivt ved erobring/bygningsendringer/befolkningsvekst; HUD-verdier oppdateres separat. `plot` kopierer en byte til `$0400` og den tilsvarende fargen ved base `$D800` gjennom et par zero-page pointers. Maskinkodetestene instrumenterer alle `plot`-kall under initialisering av representative verdenskart og verifiserer at X er 0–39, Y er 0–24.

## Spillmotor

`main_loop`: venter på rasterlinje 250, oppdaterer SID, leser tastatur/joystick, og simulerer hver 16/19 videoframes. `simulate`: balanserer jobber, oppdaterer økonomi, forskning, AI-autoøkonomi, vedlikeholder berørte sektorer og måler seier. `ai_turn`: roterer fiendefraksjon + kildesektor og gjør ett tilstøtende strategisk angrep dersom vilkårene oppfylles. `do_attack`: felles deterministisk angreps- og beleiringsmotor for alle eier-ID-er. `reinforce`: separat, kapasitetsbeskyttet vennlig overføring.

Det er **ingen** grafikkblitter, sprite-multiplexer, 8 KB bitmap-tegnearbeid, ekstern musikkplayer, harddiskbehov eller bank-switching for gameplay. Datastrukturer er 12 byte per sektorarray og bruker rent 8-bit regnskap.

## Verifikasjonsgrense

`tests/cpu6502.py` kjører ekte utsendte opcodes med minne/registre og egne KERNAL-GETIN-stubber. Verktøyet **emulerer ikke** VIC-II syklustiming, SID-analogt filter, real joystick multiplexing, 1541 mekanikk eller KERNAL IRQ atferd. Ingen tilsvarende påstander følger av at CPU-testene består. Menneskelig spillbarhet/balanse gjennom alle 28 nivåer må også vurderes manuelt.


## v3 persistence and runtime data

Memory `$C000` contains a temporary serialized state file after O/I. KERNAL LOAD uses secondary address 0 to relocate trusted file contents regardless of embedded PRG header. The game state block is `[owner, cpu_count]` inclusive; the `doctrine` array is part of this contiguous RAM block. This state has a checksum and version but is **not** isolated from oversize I/O at the KERNAL layer. Disk I/O is blocking and is called on user keypress only, never from raster IRQ. No persistent SQL/flash storage or expansion hardware.
