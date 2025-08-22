from __future__ import annotations

import os
import logging
from typing import List, Dict, Any, Optional
import json

import numpy as np

try:
    import psycopg2
    from psycopg2.extras import execute_values
    import sqlalchemy as sa
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
except ImportError as import_error:
    psycopg2 = None
    sa = None
    create_engine = None
    sessionmaker = None

logger = logging.getLogger(__name__)


class PgVectorStore:
    """PostgreSQL vector store using pgvector extension"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5433,
        database: str = "hinthint",
        user: str = "postgres",
        password: str = "postgres",
        table_name: str = "products",
        dimension: int = 384,
    ) -> None:
        if psycopg2 is None or sa is None:
            raise ImportError(
                "Required dependencies not installed. Install: pip install psycopg2-binary sqlalchemy pgvector"
            )
        
        # Get connection params from environment, fall back to passed values
        self.host = os.getenv("POSTGRES_HOST", host)
        self.port = int(os.getenv("POSTGRES_PORT", port))
        self.database = os.getenv("POSTGRES_DB", database)
        self.user = os.getenv("POSTGRES_USER", user)
        self.password = os.getenv("POSTGRES_PASSWORD", password)
        self.table_name = table_name
        self.dimension = dimension
        self.index_type = os.getenv("PGVECTOR_INDEX", "ivfflat").lower()
        self.ivf_lists = int(os.getenv("PGVECTOR_LISTS", "100"))
        # default probes to lists for high recall on small datasets
        self.ivf_probes = int(os.getenv("PGVECTOR_PROBES", str(self.ivf_lists)))
        # exact mode forces sequential scan (useful for tiny datasets)
        self.exact_mode = os.getenv("PGVECTOR_EXACT", "0").lower() in ("1", "true", "yes", "y")
        
        # Build connection string
        self.connection_string = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        
        # Create engine and session
        self.engine = create_engine(self.connection_string)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Initialize database schema
        self._ensure_database_setup()
    
    def _ensure_database_setup(self) -> None:
        
        try:
            # Enable pgvector extension
            with self.engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id INTEGER PRIMARY KEY,
                    embedding vector({self.dimension}),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
                conn.execute(text(create_table_sql))
                conn.commit()
                
                if self.index_type == "hnsw":
                    index_sql = f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_hnsw 
                    ON {self.table_name} USING hnsw (embedding vector_cosine_ops);
                    """
                else:
                    index_sql = f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx 
                    ON {self.table_name} USING ivfflat (embedding vector_cosine_ops) 
                    WITH (lists = {self.ivf_lists});
                    """
                conn.execute(text(index_sql))
                conn.commit()

                conn.execute(text(f"ANALYZE {self.table_name};"))
                conn.commit()
                
            logger.info(f"Database setup completed. Table '{self.table_name}' ready with pgvector extension.")
            
        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            raise
    
    def add_embeddings(
        self,
        embeddings: np.ndarray,
        metadata: List[Dict[str, Any]],
        ids: List[Any],
        batch_size: int = 100,
    ) -> None:
        
        if len(embeddings) != len(metadata) or len(embeddings) != len(ids):
            raise ValueError("Lengths of embeddings, metadata, and ids must match")
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"DELETE FROM {self.table_name}"))
                conn.commit()
            
            data_to_insert = []
            for emb, md, id_val in zip(embeddings, metadata, ids):
                data_to_insert.append({
                    'id': int(id_val),
                    'embedding': emb.tolist(),  # Convert numpy array to list
                    'metadata': json.dumps(md)  # Convert dict to JSON string
                })
            
            for i in range(0, len(data_to_insert), batch_size):
                batch = data_to_insert[i:i + batch_size]
                
                with self.engine.connect() as conn:
                    for item in batch:
                        insert_sql = """
                        INSERT INTO {} (id, embedding, metadata) 
                        VALUES (:id, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
                        ON CONFLICT (id) DO UPDATE SET 
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            created_at = CURRENT_TIMESTAMP
                        """.format(self.table_name)
                        
                        conn.execute(text(insert_sql), {
                            'id': item['id'],
                            'embedding': str(item['embedding']),
                            'metadata': item['metadata']
                        })
                    conn.commit()
            
            logger.info(f"Successfully added {len(embeddings)} embeddings to {self.table_name}")
            
        except Exception as e:
            logger.error(f"Failed to add embeddings: {e}")
            raise
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        
        try:
            query_vector = query_embedding.tolist()
            
            search_sql = """
            SELECT 
                id,
                metadata,
                1 - (embedding <=> CAST(:query_vector AS vector)) as similarity
            FROM {}
            ORDER BY embedding <=> CAST(:query_vector AS vector)
            LIMIT :top_k
            """.format(self.table_name)
            
            with self.engine.connect() as conn:
                if self.index_type == "ivfflat":
                    try:
                        conn.execute(text("SET LOCAL ivfflat.probes = :p"), {"p": self.ivf_probes})
                    except Exception:
                        pass
                if self.exact_mode:
                    try:
                        conn.execute(text("SET LOCAL enable_indexscan = off"))
                        conn.execute(text("SET LOCAL enable_bitmapscan = off"))
                    except Exception:
                        pass

                result = conn.execute(
                    text(search_sql), 
                    {
                        'query_vector': str(query_vector),
                        'top_k': top_k
                    }
                )
                rows = result.fetchall()
            
            results = []
            for row in rows:
                md_raw = row[1]
                if isinstance(md_raw, (str, bytes, bytearray)):
                    try:
                        md = json.loads(md_raw)
                    except Exception:
                        md = {}
                elif isinstance(md_raw, dict):
                    md = md_raw
                else:
                    try:
                        md = json.loads(md_raw) if md_raw is not None else {}
                    except Exception:
                        md = {}

                results.append({
                    "id": str(row[0]),
                    "metadata": md,
                    "similarity": float(row[2]),
                })
            
            logger.info(f"Found {len(results)} results for vector search")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def close(self) -> None:
        """Close database connections"""
        if hasattr(self, 'session'):
            self.session.close()
        if hasattr(self, 'engine'):
            self.engine.dispose()