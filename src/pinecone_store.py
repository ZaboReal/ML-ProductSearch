from __future__ import annotations

import os
import logging
from typing import List, Dict, Any

import numpy as np

try:
    from pinecone import Pinecone, ServerlessSpec  # type: ignore
except Exception as import_error:
    Pinecone = None
    ServerlessSpec = None


logger = logging.getLogger(__name__)


class PineconeVectorStore:

    def __init__(
        self,
        api_key: str | None = None,
        index_name: str = "products-index",
        dimension: int = 384,
        metric: str = "cosine",
        cloud: str | None = None,
        region: str | None = None,
    ) -> None:
        if Pinecone is None or ServerlessSpec is None:
            raise ImportError(
                "pinecone-client v3 is not installed. Add 'pinecone-client' to requirements and pip install."
            )

        self.api_key = api_key or os.getenv("PINECONE_API_KEY") or "pcsk_6xYoJ8_6Gfz4DauzLFe4VdGrnRJ6gMwgG54meqLcnAjhFbuYRK79WhdmfyQGuYadmUBuwF"
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY is required for PineconeVectorStore")

        self.index_name = os.getenv("PINECONE_INDEX", index_name)
        self.dimension = dimension
        self.metric = metric
        self.cloud = cloud or os.getenv("PINECONE_CLOUD", "aws")
        self.region = region or os.getenv("PINECONE_REGION", "us-east-1")

        # Init client and ensure index exists (serverless)
        self.pc = Pinecone(api_key=self.api_key)
        self._ensure_index()
        self.index = self.pc.Index(self.index_name)

    def _ensure_index(self) -> None:
        if not self.pc.has_index(self.index_name):
            logger.info(
                f"Creating Pinecone serverless index '{self.index_name}' (dimension={self.dimension}, metric={self.metric}, cloud={self.cloud}, region={self.region})"
            )
            self.pc.create_index(
                name=self.index_name,
                vector_type="dense",
                dimension=self.dimension,
                metric=self.metric,
                spec=ServerlessSpec(cloud=self.cloud, region=self.region),
                deletion_protection="disabled",
            )

    def add_embeddings(
        self,
        embeddings: np.ndarray,
        metadata: List[Dict[str, Any]],
        ids: List[Any],
        namespace: str | None = None,
        batch_size: int = 100,
    ) -> None:
        if len(embeddings) != len(metadata) or len(embeddings) != len(ids):
            raise ValueError("Lengths of embeddings, metadata, and ids must match")

        items: List[Dict[str, Any]] = []
        for vec, md, _id in zip(embeddings, metadata, ids):
            items.append({
                "id": str(_id),
                "values": vec.tolist(),
                "metadata": md,
            })

        for start in range(0, len(items), batch_size):
            batch = items[start:start + batch_size]
            self.index.upsert(vectors=batch, namespace=namespace)

        logger.info(f"Upserted {len(items)} vectors into Pinecone index '{self.index_name}'")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        namespace: str | None = None,
        filter: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        res = self.index.query(
            vector=query_embedding.tolist(),
            top_k=top_k,
            include_metadata=True,
            namespace=namespace,
            filter=filter,
        )

        results: List[Dict[str, Any]] = []
        for m in getattr(res, "matches", []) or []:
            results.append({
                "id": m["id"] if isinstance(m, dict) else getattr(m, "id", None),
                "metadata": m.get("metadata") if isinstance(m, dict) else getattr(m, "metadata", {}),
                "similarity": float(m.get("score", 0.0)) if isinstance(m, dict) else float(getattr(m, "score", 0.0)),
            })
        return results


