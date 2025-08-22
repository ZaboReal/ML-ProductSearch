
A semantic product search system with support for multiple vector backends.

The writeups/diagram/architecture are all under docs folder

## Vector Backend Support

The system now supports multiple vector backends:

- **pgvector** (default): PostgreSQL with pgvector extension - runs locally with Docker
- **pinecone**: Pinecone cloud vector database
- **memory**: In-memory vector storage (fallback)


### Environment Variables

Create a `.env` file in the project root (it is added to github here for project sake):

```env
# Vector backend selection
VECTOR_BACKEND=pgvector (or pinecone or memory) [IF KEPT EMPTY IT WILL DEFAULT TO pgvector]

# PostgreSQL configuration (for pgvector)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=hinthint
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres [IMPORTANT: your password must match the password set for username at port 5432]

```

## How to run

### Prerequisites
- Python 3.10+
- pip
- Docker 
- postgresql (you must also have pgvector cloned and installed: see https://github.com/pgvector/pgvector for setup if not installed )

### Option A: One‑liner (bash) [RECOMMENDED]
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
- Runs ~10 test queries against each available backend
- Logs top 5 per query with: ID, title, price
- Prints latency stats (avg and P95)
- Automatically starts and waits for pgvector Docker when needed

# Example pgvector query results
- **Query: running shoes under $120**
  1. [357] Classic Leather Sneakers $44.05
  2. [189] Classic Leather Sneakers $69.41
  3. [55] Classic Leather Sneakers $57.83
  4. [50] Athletic Leggings $109.21
  5. [30] Chelsea Boots $40.46

- **Query: wireless earbuds under $80**
  1. [266] Wireless Earbuds $33.80
  2. [147] Noise-Cancelling Headphones $65.14
  3. [159] Noise-Cancelling Headphones $31.25
  4. [340] Laptop Sleeve $43.53
  5. [436] Bluetooth Speaker $64.24

- **Query: office chair ergonomic under $200**
  1. [301] Dining Chair $123.80
  2. [379] Dining Chair $155.49
  3. [434] Portable Projector $119.96
  4. [350] Mechanical Keyboard $184.03
  5. [52] Foldable Phone Stand $49.98

