#!/usr/bin/env python
import os
import time
import statistics
from pathlib import Path
import argparse

import subprocess
import sys

from dotenv import load_dotenv

# Ensure src on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ingest import DataIngester
from embed_and_load import ProductEmbedder
from search import ProductSearcher


QUERIES = [
    "linen summer dress under $300",
    "running shoes under $120",
    "wireless earbuds under $80",
    "coffee maker under $100",
    "gaming mouse",
    "4k tv under $600",
    "winter jacket",
    "yoga mat under $30",
    "portable bluetooth speaker",
    "office chair ergonomic under $200",
]


def start_pgvector_if_needed():
    if os.getenv("VECTOR_BACKEND", "pgvector").lower() != "pgvector":
        return
    try:
        # start container
        try:
            subprocess.run(["docker-compose", "up", "-d", "postgres"], check=True)
        except Exception:
            subprocess.run(["docker", "compose", "up", "-d", "postgres"], check=True)
        # wait until ready
        print("[pgvector] waiting for database...")
        max_attempts = 30
        for i in range(max_attempts):
            env = os.environ.copy()
            env["PGPASSWORD"] = os.getenv("POSTGRES_PASSWORD", "postgres")
            cmd = [
                "psql",
                "-h",
                os.getenv("POSTGRES_HOST", "localhost"),
                "-p",
                os.getenv("POSTGRES_PORT", "5433"),
                "-U",
                os.getenv("POSTGRES_USER", "postgres"),
                "-d",
                os.getenv("POSTGRES_DB", "hinthint"),
                "-c",
                "SELECT 1;",
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, env=env)
                print("[pgvector] ready")
                return
            except Exception:
                time.sleep(2)
        print("[pgvector] WARNING: database not confirmed ready after timeout")
    except Exception as e:
        print(f"[pgvector] WARNING: failed to manage docker: {e}")


def eval_backend(backend: str):
    print(f"\n=== Backend: {backend.upper()} ===")
    os.environ["VECTOR_BACKEND"] = backend

    if backend == "pgvector":
        start_pgvector_if_needed()

    embedder = ProductEmbedder()

    # Always ingest and embed for the selected backend (loads/upserts where applicable)
    ingester = DataIngester()
    df = ingester.load_products()
    df = ingester.preprocess_data(df)
    vector_store = embedder.embed_products(df)

    searcher = ProductSearcher(vector_store)

    latencies = []
    all_results = []
    for q in QUERIES:
        t0 = time.perf_counter()
        results = searcher.simple_search(q, top_k=5)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies.append(dt)

        # Log compact results
        rows = [
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "price": r.get("price"),
            }
            for r in results
        ]
        all_results.append((q, rows))

    # Print results
    for q, rows in all_results:
        print(f"\nQuery: {q}")
        for i, r in enumerate(rows, 1):
            price = r["price"]
            price_str = f"${price:.2f}" if isinstance(price, (int, float)) else ""
            print(f"  {i}. [{r['id']}] {r['title']} {price_str}")

    # Latency stats
    avg_ms = statistics.mean(latencies) if latencies else 0.0
    p95_ms = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies) if latencies else 0.0
    print(f"\nLatency (ms): avg={avg_ms:.2f}, p95={p95_ms:.2f}")


def main():
    load_dotenv(ROOT / ".env")
    os.chdir(ROOT)

    parser = argparse.ArgumentParser(description="Mini evaluation harness for vector backends")
    parser.add_argument(
        "--backends",
        type=str,
        default=None,
        help="Comma-separated list of backends to test (memory,pgvector,pinecone). If omitted, uses VECTOR_BACKEND if set, otherwise defaults to memory,pgvector (+pinecone if configured).",
    )
    args = parser.parse_args()

    selected: list[str]
    if args.backends:
        selected = [b.strip().lower() for b in args.backends.split(",") if b.strip()]
    else:
        env_backend = os.getenv("VECTOR_BACKEND")
        if env_backend:
            selected = [env_backend.lower()]
        else:
            selected = ["memory", "pgvector"]
            if os.getenv("PINECONE_API_KEY"):
                selected.append("pinecone")

    for b in selected:
        eval_backend(b)


if __name__ == "__main__":
    main()


