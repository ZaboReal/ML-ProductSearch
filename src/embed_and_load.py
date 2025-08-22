import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict, Any, Optional
import os
import pickle
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        try:
            logger.info(f"Loading model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([])
        
        try:
            logger.info(f"Generating embeddings for {len(texts)} texts")
            embeddings = self.model.encode(texts, show_progress_bar=True)
            logger.info(f"Generated embeddings with shape: {embeddings.shape}")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def generate_single_embedding(self, text: str) -> np.ndarray:
        return self.generate_embeddings([text])[0]


class VectorDatabase:
    def __init__(self):
        self.embeddings = []
        self.metadata = []
        self.ids = []
    
    def add_embeddings(self, embeddings: np.ndarray, metadata: List[Dict], ids: List[Any]):
        if len(embeddings) != len(metadata) or len(embeddings) != len(ids):
            raise ValueError("Lengths of embeddings, metadata, and ids must match")
        
        self.embeddings.extend(embeddings)
        self.metadata.extend(metadata)
        self.ids.extend(ids)
        
        logger.info(f"Added {len(embeddings)} embeddings to database")
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        if not self.embeddings:
            return []
        
        embeddings_array = np.array(self.embeddings)
        similarities = np.dot(embeddings_array, query_embedding) / (
            np.linalg.norm(embeddings_array, axis=1) * np.linalg.norm(query_embedding)
        )
        
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                'id': self.ids[idx],
                'metadata': self.metadata[idx],
                'similarity': float(similarities[idx])
            })
        
        return results
    
    def save(self, filepath: str):
        data = {
            'embeddings': self.embeddings,
            'metadata': self.metadata,
            'ids': self.ids
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Database saved to {filepath}")
    
    def load(self, filepath: str):
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.embeddings = data['embeddings']
        self.metadata = data['metadata']
        self.ids = data['ids']
        
        logger.info(f"Database loaded from {filepath}")


class ProductEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.embedding_generator = EmbeddingGenerator(model_name)
        self.vector_db = None
        self.backend_type = os.getenv("VECTOR_BACKEND", "pgvector").lower()
        
        # Initialize the appropriate vector store based on environment variable
        if self.backend_type == "pinecone":
            self._init_pinecone()
        elif self.backend_type == "pgvector":
            self._init_pgvector()
        elif self.backend_type == "memory":
            self.vector_db = VectorDatabase()
            logger.info("Using in-memory vector store")
        else:
            logger.warning(f"Unknown VECTOR_BACKEND '{self.backend_type}', falling back to in-memory store")
            self.vector_db = VectorDatabase()
            self.backend_type = "memory"
    
    def _init_pinecone(self):
        try:
            from pinecone_store import PineconeVectorStore
            self.vector_db = PineconeVectorStore(dimension=384, metric="cosine")
            logger.info("Using Pinecone vector store")
        except Exception as e:
            logger.warning(f"Pinecone not available, falling back to in-memory store: {e}")
            self.vector_db = VectorDatabase()
            self.backend_type = "memory"
    
    def _init_pgvector(self):
        try:
            from pgvector_store import PgVectorStore
            self.vector_db = PgVectorStore(dimension=384)
            logger.info("Using pgvector (PostgreSQL) vector store")
        except Exception as e:
            logger.warning(f"pgvector not available, falling back to in-memory store: {e}")
            self.vector_db = VectorDatabase()
            self.backend_type = "memory"
    
    def create_product_texts(self, df: pd.DataFrame) -> List[str]:
        required_cols = {"title", "description", "category"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns for text creation: {missing}")

        texts: List[str] = []
        for _, row in df.iterrows():
            title = str(row["title"]).strip()
            description = str(row["description"]).strip()
            category = str(row["category"]).strip()
            text = f"{title}. {description}. Category: {category}."
            texts.append(text)

        return texts
    
    def embed_products(self, df: pd.DataFrame):
        texts = self.create_product_texts(df)
        embeddings = self.embedding_generator.generate_embeddings(texts)
        metadata = df[["id", "category", "title", "description", "price", "url"]].to_dict('records')
        ids = df['id'].tolist()
        
        # Add embeddings to the vector store
        self.vector_db.add_embeddings(embeddings, metadata, ids)
        
        return self.vector_db
    
    def save_embeddings(self, filepath: str = "data/product_embeddings.pkl"):
        if self.backend_type in ["pinecone", "pgvector"]:
            logger.info(f"{self.backend_type} in use; skipping local pickle save.")
            return
        if hasattr(self.vector_db, "save"):
            self.vector_db.save(filepath)
        else:
            logger.info("Active vector store does not support saving; skipping.")
    
    def load_embeddings(self, filepath: str = "data/product_embeddings.pkl"):
        if self.backend_type in ["pinecone", "pgvector"]:
            logger.info(f"{self.backend_type} in use; loading from pickle not applicable.")
            return
        if hasattr(self.vector_db, "load"):
            self.vector_db.load(filepath)
        else:
            logger.info("Active vector store does not support loading from file; skipping.")


def main():
    from ingest import DataIngester
    
    ingester = DataIngester()
    products_df = ingester.load_products()
    clean_df = ingester.preprocess_data(products_df)
    
    embedder = ProductEmbedder()
    vector_db = embedder.embed_products(clean_df)
    
    embedder.save_embeddings()
    
    print("Embedding generation completed successfully!")
    print(f"Generated embeddings for {len(clean_df)} products")
    
    return vector_db


if __name__ == "__main__":
    main()
