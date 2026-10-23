#!/bin/sh
# The independent selector uses the same disk and turbo-floppy defaults.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VICE_SELECTOR=1 exec "$ROOT/tools/run_vice.sh" "$@"
