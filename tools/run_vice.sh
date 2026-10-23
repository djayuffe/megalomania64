#!/bin/sh
# Prefer the local native integration disk, then the full and fallback D64s.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
EMULATOR=${VICE_BIN:-}
if [ -z "$EMULATOR" ]; then
  if command -v x64sc >/dev/null 2>&1; then EMULATOR=x64sc
  elif command -v x64 >/dev/null 2>&1; then EMULATOR=x64
  else
    printf '%s\n' 'VICE (x64sc/x64) not found. Install VICE, or set VICE_BIN=/path/to/x64sc' >&2
    exit 127
  fi
fi
if [ "$#" -gt 0 ]; then
  DISK=$1
elif [ -f "$ROOT/../recovery/MegaLoMania64_native.d81" ]; then
  DISK=$ROOT/../recovery/MegaLoMania64_native.d81
elif [ -f "$ROOT/../recovery/MegaLoMania64_full.d64" ]; then
  DISK=$ROOT/../recovery/MegaLoMania64_full.d64
else
  DISK=$ROOT/dist/MegaLoMania64.d64
fi
DRIVE_TYPE=1541
case "$DISK" in *.d81|*.D81) DRIVE_TYPE=1581 ;; esac
if [ "${VICE_SELECTOR:-0}" = 1 ]; then
  SELECTOR=${VICE_SELECTOR_FILE:-"$ROOT/../recovery/native/files/NGSELECT"}
  if [ ! -f "$SELECTOR" ]; then
    printf '%s\n' 'Build the native disk and NGSELECT module first.' >&2
    exit 1
  fi
  set -- -8 "$DISK" -autostartprgmode 1 -autostart "$SELECTOR"
else
  set -- -autostart "$DISK"
fi
if [ "${VICE_TURBO_FLOPPY:-1}" = 1 ]; then
  exec "$EMULATOR" -model "${VICE_MODEL:-c64c}" -drive8type "$DRIVE_TYPE" -sound +warp -soundrecdev "" -virtualdev8 +drive8truedrive -autostart-warp "$@"
fi
exec "$EMULATOR" -model "${VICE_MODEL:-c64c}" -drive8type "$DRIVE_TYPE" -sound +warp -soundrecdev "" -drive8truedrive +virtualdev8 -autostart "$@"
