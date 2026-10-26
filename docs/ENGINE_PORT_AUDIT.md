# Engine integration audit — 26 October 2026

This records the 26 October baseline. The subsequent
[character-dialogue port](DIALOGUE_PORT.md) adds a ninth presentation overlay,
original portraits and speaker-specific recordings; its documented missing
source and animation limits supersede the dialogue gap listed below.

The eight streamed engines are built and linked together on the native disk.
The shared sample/engine window is `$EF00–$FFF9`. Cache ownership is exclusive:
loading sample bytes invalidates the engine identity, and loading engine bytes
invalidates the sample identity. Partial decode failures invalidate both.
Active audio blocks a new engine load. These conditions are exercised by host
tests executing the production loader functions, and by live VICE gameplay.

The startup selector request consumer now executes in the already-loaded combat
bank. The audited build places resident code/data through `$C154`, below the
`$C200` software-stack guard. The combat bank ends at `$EE94`, below the shared
overlay window. These addresses belong to this build; subsequent builds must
use their own linker map.

Selector fixes include valid NART filenames for all 28 islands, the correct ten
sprite ages, independent two-digit island selection and U-key user selection,
cache restoration on menu redraw and invalidation on preview entry. The full
2048-byte charset is preserved: mapping and inks use `$C000`/`$C100` instead of
overwriting font bytes. Selector sprites use `$3200–$333F` instead of the live
sound timer at `$319C`. KERNAL menu letter codes are translated to native font
codes. Diplomacy response text stays on its status row so help text cannot
overwrite it.

Validation performed:

- 94 host/6502 tests across gameplay core, native support, native gameplay,
  engine loading and selector behavior.
- Full native runtime verifier on PAL and NTSC: bootstrap, terrain, military,
  AI, diplomacy, complete effects/voices, save/load, campaign and stack guard.
- All 29 selector previews and selected-user gameplay handoff on PAL and NTSC.
- Exact selector font, complete 144-byte mapping and selected sprite-bank bytes
  checked in VICE; rendered selector inspected.
- Frozen intro hashes and private content verified unchanged.

This is integration evidence, not a claim that every original presentation or
interaction has been ported. The remaining known gaps in GAMEPLAY_PORT.md are
the alternating DOS deployment interaction and remembered computer starts on
island re-entry, dialogue artwork, character-specific voices and exact dialogue
scheduling. Complete human campaign balance and physical C64 timing also remain
unverified. The native resident coordinators, streamed engines, selector and
asset banks form different parts of the port; the eight engine files alone do
not represent the entire original executable.
