
The writeups/diagram/architecture are all under docs folder

## How to run

### Prereqs
- Python 3.10+
- pip

### Option A: One‑liner (bash)
```
./scripts/run_all.sh
# then open http://127.0.0.1:8000
```

### Option B: Manual steps
```
pip install -r requirements.txt

# (optional) sanity check ingest
python src/ingest.py

# generate embeddings and upsert to Pinecone if configured (auto configured with my apikey)
python src/embed_and_load.py

# run web app
python src/app.py
# open http://127.0.0.1:8000
```

### CLI search (optional)
```
python src/search.py "linen summer dress under 300"
```

