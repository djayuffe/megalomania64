# C64C/VICE hardware acceptance test plan (NOT yet executed)

## Environment

- VICE x64sc PAL (stock C64 ROMs), x64sc NTSC, and a real C64C with 1541, SD2IEC or compatible writable disk image.
- Load disk: `LOAD"MEGALOMANIA",8,1` then `RUN`.

## Required smoke and acceptance gates

1. Boot all modes and verify title, map colour registers, sprite and HUD text are stable. Verify keyboard scan and joystick port 2 (no CIA contention) for >5 minutes.
2. Stay in actual game loop 30 minutes; monitor frame-time/raster and badlines. Inspect $D012 wait-loop behaviour on PAL and NTSC; confirm no long stall/hang.
3. Win an island with legitimate commands; advance with C; verify changing terrain and tech display. Lose a stage; verify N restarts. Use L plus `01` and `28` to select checkpoints.
4. Choose doctrine Q, test industry ore bonus, attack and defense in actual game, AI uses workers without going negative.
5. On writable *copy*, press O to save. Inspect directory: file `ML64SAVE` exists; press N and then I to restore; verify all 12 sector population/resources, source/selection, stages and rivals. Save again to same slot and repeat. IMPORTANT: exercise `@` replace with actual DOS; historical 1541 may have save-with-replace issues.
6. Disconnect drive / write-protect disk and try O; inspect error, game state still intact. Load missing file and damaged/wrong version; game must reject.
7. Open game via a different video standard (PAL↔NTSC) and load; verify new frame divider and visual assets.
8. Audio: hear music on SID voices 2/3 and action SFX on voice 1. Validate volumes on both 6581/8580. Confirm no stuck notes after pause/restart.
9. Validate sprite vs screen at boundaries x0..x3, y0..y2, no scrolling/collision.

**Gate to production/hardware-verified label**: record actual VICE/real-system results for every test, with video/serial logs or screenshots, and correct failures before upgrading confidence status.

## v4 additions (all NOT yet executed)

10. **Boot and IRQ.** Title appears; colour-cycled logo; raster bars visible (expect slight edge jitter, none after dismissal; border returns to blue). Any key and joystick FIRE both leave the title. RUN/STOP+RESTORE still returns to BASIC. No cursor-blink artefacts anywhere on screen after 5 minutes.
11. **Frame pacing.** One game tick per 16 (PAL) / 19 (NTSC) frames while idle and while the AI is busy; pause/resume does not burst; after a disk operation time does not jump more than 8 frames.
12. **Music.** Tunes change with epoch (islands 1–12 / 13–21 / 22–28 → ancient / medieval / industrial); title tune differs; no hanging note after pause or disk access; SFX on voice 1 still audible over music.
13. **Joystick.** Direction edges move one step; diagonal moves once; FIRE tap = ENTER/raid; all 8 chords work on a real stick and cancel the tap; FIRE on pause/victory/defeat screens. No phantom keystrokes from stick movement.
14. **Diplomacy.** `E` on a weaker/stronger rival gives refusal/acceptance; AI stays off you for 90 ticks; attacking the partner prints `YOU BROKE THE TRUCE!`; `PACT:` HUD counts down.
15. **Inventions / U.** Era weapon on HUD changes per island group; rank-up message; `U` ladder on a fresh sector.
16. **Disk, the important one.** Use a **copy** of the disk. `O` twice in a row (second must replace the first): directory shows one `ML64SAVE`, message `GAME SAVED AND VERIFIED`; screen is blank and sprites vanish only during the access and return afterwards; no "SAVING" text over the map. `I` after `N` restores everything incl. truces. Boot from device 9/10 and repeat (device follows the boot drive). Write-protect the disk: `O` must report `DISK/SAVE ERROR`, never `SAVED`. Test SD2IEC/Ultimate/real 1541.
17. **Source marker.** Sprite 1 diamond sits in the army-source sector, is visible next to the cursor and survives island changes and loads.

**Gate to a "hardware-verified" label:** record the result of every numbered test above (video, screenshots or logs) and fix failures first.
