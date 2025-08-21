#!/usr/bin/env bash
set -Eeuo pipefail

# Move to project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Load environment variables if .env exists
if [[ -f ".env" ]]; then
  export $(grep -v '^#' .env | xargs || true)
fi

# Ensure deps
python -m pip install -r requirements.txt >/dev/null

echo "Running evaluation harness..."
exec python scripts/eval_harness.py "$@"


