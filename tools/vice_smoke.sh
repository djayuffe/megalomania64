#!/bin/bash
# Real-emulator smoke test (VICE 3.x x64sc, headless via xvfb). Needs the C64/DRIVES ROMs installed.
# Boots dist/MegaLoMania64.d64 on PAL and NTSC, screenshots the title and (after a key) the map.
# The virtual device is used for the disk (KERNAL traps), NOT a hardware-level 1541.
set -e
cd "$(dirname "$0")/.."
OUT=${1:-build/vice}; mkdir -p "$OUT"
run() { # name model keybuf cycles
  xvfb-run -a -s "-screen 0 800x600x24" x64sc -default +sound -warp -model "$2" -virtualdev8 +drive8truedrive \
    -autostart dist/MegaLoMania64.d64 -limitcycles "$4" -exitscreenshot "$OUT/$1.png" ${3:+-keybuf "$3" -keybuf-delay 3000} >"$OUT/$1.log" 2>&1 || true
  test -s "$OUT/$1.png" && echo "wrote $OUT/$1.png"
}
run title_pal  pal  ""  200000000
run title_ntsc ntsc ""  200000000
run map_pal    pal  " " 600000000
run map_ntsc   ntsc " " 600000000
