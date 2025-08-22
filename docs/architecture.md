# Product Search System Architecture


## System Components

### 1. Data Layer (`/data/`)
- **products.csv**: Product data with fields: `id`, `category`, `title`, `description`, `price`, `url`
- **product_embeddings.pkl**: Serialized embeddings for local runs (skipped when using Pinecone)

### 2. Core Modules (`/src/`)

#### Data Ingestion (`ingest.py`)
- **DataIngester**: Handles loading and preprocessing of product data
- **Data validation**: Ensures data quality and completeness
- **Data cleaning**: Removes duplicates, handles missing values, converts data types

#### Embedding Generation (`embed_and_load.py`)
- **EmbeddingGenerator**: Uses Sentence Transformers (`sentence-transformers/all-MiniLM-L6-v2`, 384-d, cosine) to generate text embeddings
- **Vector Store** (configurable via `VECTOR_BACKEND` environment variable):
  - **pgvector** (default): PostgreSQL with pgvector extension (`dimension=384`, `cosine`)
  - **pinecone**: Pinecone serverless index (`dense`, `cosine`, `dimension=384`)
  - **memory**: In-memory vector database (fallback, local only)
- **ProductEmbedder**: Orchestrates embedding generation and upserts to the active vector store

#### Search Engine (`search.py`)
- **ProductSearcher**: Core semantic search; queries the active vector store
- **SearchAPI**: High-level API for search operations
- **Search types**:
  - Semantic search by query
  - Category-based search
  - Price range filtering
 
#### Utilities (`util.py`)
- **Configuration management**: Loading/saving system configuration
- **Text processing**: Cleaning and normalizing text
- **Data validation**: Ensuring data quality (uses centralized schema)
- **Export functions**: Saving results in various formats
- **Formatting helpers**: Price and product info formatting

#### Centralized Schema (`schemas.py` and `docs/product.schema.json`)
- **`src/schemas.py`**: Pydantic `Product` model and `REQUIRED_PRODUCT_COLUMNS`
- **`docs/product.schema.json`**: Generated JSON Schema for documentation/validation

### 3. Documentation (`/docs/`)
- **architecture.md**: system architecture documentation
- **diagram.mmd**: Mermaid diagram showing system flow
- **writeup.md**: The overarching summary of the project


## Data Flow

```
1. Data Loading
   products.csv → DataIngester → Clean DataFrame

2. Embedding Generation
   Clean DataFrame → ProductEmbedder → Sentence Transformers (384-d) → Vector Store
   - pgvector (default)
   - Pinecone
   - In-memory (fallback)

3. Search Operations
   User Query → EmbeddingGenerator → Vector Search → Results

4. Result Processing
   Search Results → Formatting → Export/Display
```

## pgvector Backend Details

### Implementation (`src/pgvector_store.py`)
- Initializes PostgreSQL vector search using the `pgvector` extension.
- Ensures extension and schema exist at startup:
  - Table: `products(id INTEGER PRIMARY KEY, embedding vector(384), metadata JSONB, created_at TIMESTAMP)`
  - Index: configurable approximate index (IVFFlat by default) on `embedding` with cosine ops.
- Upserts embeddings in batches, stores full product record in `metadata` (JSONB).
- Search:
  - Cosine distance via `<=>` (converted to similarity `1 - distance`).
  - Returns `id`, `metadata` (parsed JSON), and similarity.
- Tuning knobs (via env):
  - `PGVECTOR_INDEX`: `ivfflat` (default) or `hnsw`.
  - `PGVECTOR_LISTS`: IVFFlat lists (e.g., 100–1000 based on corpus size).
  - `PGVECTOR_PROBES`: IVFFlat probes per query (recall/latency tradeoff).
  - `PGVECTOR_EXACT`: `1` to prefer exact scans on tiny datasets.
  - Applies `SET LOCAL ivfflat.probes` during queries when IVFFlat is used.

### Configuration & Runtime
- Selected by `VECTOR_BACKEND=pgvector` (default).
- Connection via `POSTGRES_HOST`, `POSTGRES_PORT` (default 5433), `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
- Dockerized Postgres with pgvector:
  - `docker-compose.yml` uses `pgvector/pgvector:pg16`, maps host `5433 → 5432` to avoid local conflicts.
  - Healthcheck + optional `init.sql` for extension bootstrap.
- Scripts
  - `scripts/run_all.sh` / `scripts/run_all.py` start the container, wait for readiness, then ingest, embed, and run the app.
  - `scripts/eval_harness.(py|sh)` can spin up pgvector and run a mini benchmark across backends.
