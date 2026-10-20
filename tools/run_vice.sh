#!/bin/sh
# Run the local full disk when present, otherwise the packaged fallback D64.
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
elif [ -f "$ROOT/../recovery/MegaLoMania64_full.d64" ]; then
  DISK=$ROOT/../recovery/MegaLoMania64_full.d64
else
  DISK=$ROOT/dist/MegaLoMania64.d64
fi
if [ "${VICE_TURBO_FLOPPY:-1}" = 1 ]; then
  exec "$EMULATOR" -model "${VICE_MODEL:-c64c}" -sound +warp -soundrecdev "" -virtualdev8 +drive8truedrive -autostart-warp -autostart "$DISK"
fi
exec "$EMULATOR" -model "${VICE_MODEL:-c64c}" -sound +warp -soundrecdev "" -drive8truedrive +virtualdev8 -autostart "$DISK"
