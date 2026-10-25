# Independent scene and island selector

`NGSELECT` is a separate C64 program. It previews all 29 frozen intro scenes
and starts fresh checkpoints on any of the 28 gameplay islands. The ordinary
intro and its entry PRG are unchanged.

Build the private native disk as described in [native integration](NATIVE_INTEGRATION.md),
then run `./tools/run_selector.sh`. It attaches the same D81 and uses the turbo
floppy settings from `run_vice.sh`. Normal launches disable inherited debugger
servers and do not save temporary emulator settings. On a C64, use `LOAD"NGSELECT",8,1` then `RUN`.
The normal launcher still starts the complete intro and campaign.

- **I / G** selects intro previews or gameplay islands.
- **A / D**, or the joystick directions, selects the previous/next entry.
- Enter **two digits** to select an entry directly: 01–29 for intro, 01–28 for game.
- **Return / fire** opens the selection.
- In game mode, **1–4** chooses the human user/faction. The selected user is
  carried into the native checkpoint handoff.
- During an intro preview, **any key / fire** returns to this menu. Release the
  opening fire press before pressing it again to exit.

Story text patches reconstruct their own full background before displaying.
Credits use the frozen character/bitmap split, scrolling renderer and PAL/NTSC
70 Hz normalization. A preview stops at the scene's final scroll position and
waits for input; it does not advance to the next scene automatically.

An island selection starts a fresh checkpoint with the normal epoch population
pool and deployment preparation. It does not load a saved campaign. Island 28
uses a documented standalone fixture of 1,000 saved people per faction, yielding
100 deployable people each; there is no preceding campaign to supply reserves.
F7 remains available in gameplay to load an existing save.

When a game island is highlighted, the selector streams its converted `NART`
character atlas and matching `NSPR` sprite bank. The complete 144-character
table is shown in the gallery and four sprite frames are enabled, using the
same graphics banks that gameplay loads.

## Module boundary

- `src/gameplay/selector.asm` owns the menu, selection, preview orchestration and
  launch request. `tools/build_selector.py` makes a separate executable using the
  frozen entry's resident renderers. Its replacement entry occupies only
  `$1000–$1FFF`; the original distributed entry PRG is never rewritten.
- `src/gameplay/selector.c` validates and consumes the one-shot `SEL`, island,
  user and complemented request at `$02F0–$02F6`, and initializes a fresh checkpoint.
- `NGSTART` clears all intro/selector RAM before loading gameplay. The selector
  leaves no resident picture, menu code, decoder or graphics allocation in game.
- Scene catalog metadata lives alongside the private executable as `NGSELECT.json`;
  it is not written as a disk payload or included in the public source archive.

`tools/verify_selector.py --all-scenes` checks all 29 scene loads, story patch
backgrounds, credit scrolling, navigation, menu return, final-island handoff and
RAM reclamation in VICE. PAL and NTSC reports and screenshots stay in the private
build directory. Synthetic unit tests cover wraparound, direct selection,
checkpoint pools/reserves and preservation of the frozen renderer bytes.
