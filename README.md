
# HintHint Product Search

A semantic product search system with support for multiple vector backends.

The writeups/diagram/architecture are all under docs folder

## Vector Backend Support

The system now supports multiple vector backends:

- **pgvector** (default): PostgreSQL with pgvector extension - runs locally with Docker
- **pinecone**: Pinecone cloud vector database
- **memory**: In-memory vector storage (fallback)

### Configuration

Set the vector backend using the `VECTOR_BACKEND` environment variable:

```bash
# Use pgvector (default)
export VECTOR_BACKEND=pgvector

# Use Pinecone (requires API key)
export VECTOR_BACKEND=pinecone

# Use in-memory (no persistence)
export VECTOR_BACKEND=memory
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Vector backend selection
VECTOR_BACKEND=pgvector

# PostgreSQL configuration (for pgvector)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=hinthint
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

```

## How to run

### Prerequisites
- Python 3.10+
- pip
- Docker & Docker Compose (for pgvector backend)

### Option A: One‑liner (bash)
```bash
./scripts/run_all.sh
# then open http://127.0.0.1:8000
```

This script will:
1. Automatically start PostgreSQL with pgvector using Docker (if using pgvector backend)
2. Install Python dependencies
3. Ingest and normalize product data
4. Generate embeddings and load them into the vector store
5. Start the web application

### Option B: Python script
```bash
python scripts/run_all.py
# then open http://127.0.0.1:8000
```

### Option C: Manual steps
```bash
# Start PostgreSQL with pgvector (if using pgvector backend)
docker-compose up -d postgres

# Install dependencies
pip install -r requirements.txt

# Ingest data
python src/ingest.py

# Generate embeddings and load to vector store
python src/embed_and_load.py

# Start web app
python src/app.py
# open http://127.0.0.1:8000
```

### CLI search (optional)
```bash
python src/search.py "linen summer dress under 300"
```

### To run the evaluation tests

Bash wrapper:
```bash
./scripts/eval_harness.sh
```

Python directly:
```bash
python scripts/eval_harness.py
```
- Runs ~10 test queries against each available backend (`memory`, `pgvector`, and `pinecone` if API key present)
- Logs top 5 per query with: ID, title, price
- Prints latency stats (avg and P95)
- Automatically starts and waits for pgvector Docker when needed

## Docker Setup

The system includes a Docker Compose configuration for easy PostgreSQL setup:

```bash
# Start PostgreSQL with pgvector
docker-compose up -d

# Stop PostgreSQL
docker-compose down
```

