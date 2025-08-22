from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ingest import DataIngester
from embed_and_load import ProductEmbedder
from search import ProductSearcher


app = FastAPI(title="Product Search")


@app.on_event("startup")
def on_startup() -> None:
    if getattr(app.state, "searcher", None) is not None:
        return
    embedder = ProductEmbedder()
    if embedder.backend_type == "memory":
        ingester = DataIngester()
        df = ingester.load_products()
        df = ingester.preprocess_data(df)
        vector_store = embedder.embed_products(df)
    else:
        vector_store = embedder.vector_db

    app.state.searcher = ProductSearcher(vector_store)


@app.get("/api/search")
def api_search(query: str, k: int = 5) -> JSONResponse:
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    results = app.state.searcher.simple_search(query.strip(), top_k=max(1, min(k, 50)))
    return JSONResponse({"query": query, "results": results})


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)


