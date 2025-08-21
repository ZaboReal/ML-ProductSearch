#!/usr/bin/env bash
set -Eeuo pipefail

# Move to project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Load environment variables if .env exists
if [[ -f ".env" ]]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

# Default to pgvector if VECTOR_BACKEND is not set
export VECTOR_BACKEND="${VECTOR_BACKEND:-pgvector}"

echo "Using vector backend: $VECTOR_BACKEND"

# Use hardcoded python
PYTHON_BIN="python"

# Check if we need Docker for pgvector
if [[ "$VECTOR_BACKEND" == "pgvector" ]]; then
  # Check if Docker is available
  if ! command -v docker-compose >/dev/null 2>&1 && ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: pgvector backend requires Docker/Docker Compose but neither is available"
    echo "Please install Docker or set VECTOR_BACKEND=pinecone in your .env file"
    exit 1
  fi
  
  echo "[0/5] Setting up PostgreSQL with pgvector..."
  
  # Stop any existing container to avoid conflicts
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose down postgres 2>/dev/null || true
    docker-compose up -d postgres
  else
    docker compose down postgres 2>/dev/null || true
    docker compose up -d postgres
  fi
  
  # Wait for PostgreSQL container to be ready
  echo "Waiting for PostgreSQL container to be ready..."
  max_attempts=30
  attempt=0
  while [ $attempt -lt $max_attempts ]; do
    # Check if container is running and healthy
    if docker ps --filter "name=hinthint_postgres" --filter "status=running" | grep -q hinthint_postgres; then
      # Try to connect to the database
      if PGPASSWORD=postgres psql -h localhost -p 5433 -U postgres -d hinthint -c "SELECT 1;" >/dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
      fi
    fi
    echo "Attempt $((attempt + 1))/$max_attempts - PostgreSQL not ready yet..."
    sleep 2
    attempt=$((attempt + 1))
  done
  
  if [ $attempt -eq $max_attempts ]; then
    echo "ERROR: PostgreSQL container failed to start properly"
    echo "Checking container status:"
    docker ps -a --filter "name=hinthint_postgres"
    echo "Checking container logs:"
    docker logs hinthint_postgres 2>/dev/null || echo "No logs available"
    echo ""
    echo "If you have a local PostgreSQL running on port 5432, please stop it first:"
    echo "  sudo systemctl stop postgresql  # On Linux"
    echo "  brew services stop postgresql  # On macOS"
    echo "  # Or stop PostgreSQL service on Windows"
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

echo "[3/4] Generating embeddings and loading to vector store..."
"$PYTHON_BIN" src/embed_and_load.py || echo "(warn) embedding failed, continuing..."

echo "[4/4] Starting app at http://127.0.0.1:8000 ..."
exec "$PYTHON_BIN" src/app.py


