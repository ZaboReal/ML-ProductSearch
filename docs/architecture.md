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
- **Vector Store**:
  - Primary: Pinecone serverless index (`dense`, `cosine`, `dimension=384`)
  - Fallback: In-memory vector database (local only)
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
   - Pinecone serverless (preferred)
   - In-memory (fallback)

3. Search Operations
   User Query → EmbeddingGenerator → Vector Search → Results

4. Result Processing
   Search Results → Formatting → Export/Display
```
