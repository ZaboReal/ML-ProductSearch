
### Why this embedding model

I used`sentence-transformers/all-MiniLM-L6-v2` as the default embedding model for product and query text.

- The vectors and models make it somewhat fast for CPU use
- The semantics is good for short text and the cosine simlairty is what is used normally for this type of model.
- It's free and easily usable over any ecosystem.


### Schema and database structure

Centralized product schema is in `src/schemas.py` (Pydantic `Product`) and it matches `docs/product.schema.json`. Normalized columns:

- `id` (int): unique product identifier
- `category` (str)
- `title` (str)
- `description` (str)
- `price` (float, non‑negative)
- `url` (http/https)

Ingestion (`src/ingest.py`) enforces the schema: 
- trims text, title‑cases categories, forces types (`id` → int, `price` → float)
- drops duplicate rows and duplicate ids, and reorders columns. 

Vector storage has two interchangeable backends:
- I used Pinecone because it's easy to setup and see, I don't have to setup any postgres stuff. 

[IMPORTANT] : I know api keys shouldn't be stored directly in the code, I just did it here because for the purposes of this, it's just easier to set it up in here.

- Pinecone (preferred):
  - Index: dense, `dimension=384`, `metric=cosine`.
  - Metadata: the normalized product record (`id`, `category`, `title`, `description`, `price`, `url`) stored alongside vectors for filtering and display.
- In‑memory fallback:
  - Stores embeddings and metadata in process.

The search layer (`src/search.py`) is vector‑store (same interface for Pinecone and in‑memory). It encodes the query, retrieves candidates by cosine similarity, applies an optional natural‑language price filter (e.g., “under $300”), and then hybrid‑reranks with BM25 over title+description to improve the ranking.

The in-house app will deploy the search, so that it mimics an actual user search experience

### A few example queries and results


1) Query: “linen summer dress under $300”

- Linen Summer Dress ($293.20) → https://example.com/fashion/linen-summer-dress/270
- Linen Summer Dress ($92.44) → http://example.com/fashion/linen-summer-dress/18
- Linen Summer Dress ($273.20) → https://example.com/fashion/linen-summer-dress/44
- Linen Summer Dress ($260.78) → https://example.com/fashion/linen-summer-dress/198
- Linen Summer Dress ($172.42) → https://example.com/fashion/linen-summer-dress/158


2) Query: “tech over 220”

- Mechanical Keyboard ($247.03) → https://example.com/tech/mechanical-keyboard/234
- Smartwatch ($425.85) → https://example.com/tech/smartwatch/269
- Portable Projector ($245.81) → https://example.com/tech/portable-projector/199
- Fitness Tracker ($649.62) → https://example.com/tech/fitness-tracker/167
- Mechanical Keyboard ($649.22) → https://example.com/tech/mechanical-keyboard/68



### (Optional) How I’d extend this to production

- Relevance 
  - Richer hybrid scoring (metadata boosts, category/type‑aware rerank, synonym dictionaries).
  - Query normalization (strip currency symbols, unify units).
  - Explore stronger rerankers for the top‑N results.

- API and system hardening
  - Use Pinecone metadata filters server‑side to reduce bandwidth and speed up queries.
  - Add pagination, caching, and rate limiting.

- Data & indexing
  - Streaming/continuous ingestion
  - Periodic re‑embedding for catalog updates
  - dead‑record cleanup.

- Cost & scaling
  - Choose Pinecone region close to users; autoscaling policies.
  - Batch and cache embedding jobs; monitor token/throughput costs.

### Editorial tags: assignment and use in search/reranking

How to assign tags to products and use them to improve search relevance and control:

1) Tag assignment strategies
- We would have keyword rules that maintain a cmapping of tag → keyword/regex lists (with synonyms). 
- We could use an NLI model (e.g., `facebook/bart-large-mnli` or a smaller distilled variant) to score each candidate tag given a product’s title+description. Although this would be slower than rules
- The best wouldbe a hybrid build: Rules for high‑precision tags; fall back to embedding/zero‑shot for recall; add human‑in‑the‑loop review for low‑confidence cases.

2) Storage model
- Add a `tags: List[str]` field to product metadata and upsert it to the vector store.
- In Pinecone, we can store tags in `metadata.tags` (array). we can then filter: `filter={"tags": {"$in": ["minimalist"]}}` for example
  
3) Measuring quality
- Define tag‑aware metrics (CTR for “tagged” facets, success for targeted queries).
- Calibrate thresholds per tag using a labeled validation set or backtesting.


