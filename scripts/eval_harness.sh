#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env" ]]; then
  export $(grep -v '^#' .env | xargs || true)
fi

python -m pip install -r requirements.txt >/dev/null

echo "Running evaluation harness..."
exec python scripts/eval_harness.py "$@"


