#!/usr/bin/env bash
# Pre-commit hook: run the consistency drift checker.
# Installed by `design-init` into the project. The hook fails the
# commit if any error-severity drift is reported. Warnings are surfaced
# but do not block — to make warnings blocking, set `strict = true`
# under `[checker]` in `consistency.toml`.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="$ROOT/scripts/consistency.py"

if [ ! -f "$SCRIPT" ]; then
  echo "consistency: drift checker not found at $SCRIPT" >&2
  exit 1
fi

python3 "$SCRIPT" --root "$ROOT"
