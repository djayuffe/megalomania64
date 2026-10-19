#!/bin/sh
# Run a C64/C64C emulator with the packaged PRG. Requires VICE x64sc or x64.
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
exec "$EMULATOR" -autostart "$ROOT/dist/MegaLoMania64.prg"
