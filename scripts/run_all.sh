#!/usr/bin/env bash
set -Eeuo pipefail

# Move to project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Activate venv if present (optional)
if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate || true
fi

echo "[1/4] Installing requirements..."
python -m pip install -r requirements.txt

echo "[2/4] Ingesting and normalizing data..."
python src/ingest.py || echo "(warn) ingestion failed, continuing..."

echo "[3/4] Generating embeddings (and upserting to Pinecone if configured)..."
python src/embed_and_load.py || echo "(warn) embedding failed, continuing..."

echo "[4/4] Starting app at http://127.0.0.1:8000 ..."
exec python src/app.py

#!/usr/bin/env bash
set -Eeuo pipefail

# Navigate to project root (folder above this script)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Detect python executable (allow override via $PYTHON_BIN)
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python not found in PATH" >&2
    exit 1
  fi
fi

# Activate venv if present
if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate || true
fi

echo "[1/4] Installing requirements..."
"$PYTHON_BIN" -m pip install -r requirements.txt

echo "[2/4] Ingesting and normalizing data..."
"$PYTHON_BIN" src/ingest.py || echo "(warn) ingestion failed, continuing..."

echo "[3/4] Generating embeddings (and upserting to Pinecone if configured)..."
"$PYTHON_BIN" src/embed_and_load.py || echo "(warn) embedding failed, continuing..."

echo "[4/4] Starting app at http://127.0.0.1:8000 ..."
exec "$PYTHON_BIN" src/app.py


