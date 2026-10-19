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
