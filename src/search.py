import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from embed_and_load import EmbeddingGenerator, VectorDatabase
import re
from rank_bm25 import BM25Okapi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductSearcher:
    def __init__(self, vector_db: Optional[VectorDatabase] = None, 
                 embedding_generator: Optional[EmbeddingGenerator] = None):
        self.vector_db = vector_db
        self.embedding_generator = embedding_generator or EmbeddingGenerator("sentence-transformers/all-MiniLM-L6-v2")
    
    def search_products(self, query: str, top_k: int = 5, 
                       min_similarity: float = 0.0) -> List[Dict]:
        if not self.vector_db:
            raise ValueError("Vector database not initialized")
        
        query_embedding = self.embedding_generator.generate_single_embedding(query)
        results = self.vector_db.search(query_embedding, top_k=top_k)
        filtered_results = [
            result for result in results 
            if result['similarity'] >= min_similarity
        ]
        
        logger.info(f"Search completed. Found {len(filtered_results)} results for query: '{query}'")
        
        return filtered_results

    @staticmethod
    def _parse_price_constraints(query: str) -> Tuple[Optional[float], Optional[float]]:
        q = query.lower().replace(',', ' ')
        m = re.search(r'(?:between|from)\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:and|to|-)\s*\$?\s*(\d+(?:\.\d+)?)', q)
        if m:
            a = float(m.group(1)); b = float(m.group(2))
            return (min(a, b), max(a, b))
        m = re.search(r'(?:under|below|<=|less than|lt)\s*\$?\s*(\d+(?:\.\d+)?)', q)
        if m:
            return (None, float(m.group(1)))
        m = re.search(r'(?:over|above|>=|greater than|gt)\s*\$?\s*(\d+(?:\.\d+)?)', q)
        if m:
            return (float(m.group(1)), None)
        m = re.search(r'\$?\s*(\d+(?:\.\d+)?)\s*-\s*\$?\s*(\d+(?:\.\d+)?)', q)
        if m:
            a = float(m.group(1)); b = float(m.group(2))
            return (min(a, b), max(a, b))
        return (None, None)

    def simple_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        min_price, max_price = self._parse_price_constraints(query)

        raw_results = self.search_products(query, top_k=max(top_k * 10, 50))

        def price_ok(md: Dict[str, Any]) -> bool:
            price = md.get('price')
            if not isinstance(price, (int, float, np.floating)):
                return False
            if min_price is not None and price < min_price:
                return False
            if max_price is not None and price > max_price:
                return False
            return True

        if min_price is not None or max_price is not None:
            raw_results = [r for r in raw_results if price_ok(r['metadata'])]

        corpus = [
            (i, (r['metadata'].get('title') or '') + ' ' + (r['metadata'].get('description') or ''))
            for i, r in enumerate(raw_results)
        ]
        tokenized_corpus = [c.lower().split() for _, c in corpus]
        bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None
        bm25_scores = []
        if bm25:
            tokenized_query = query.lower().split()
            bm25_scores = list(bm25.get_scores(tokenized_query))
        else:
            bm25_scores = [0.0] * len(raw_results)

        if len(bm25_scores) > 0:
            bm_min, bm_max = float(min(bm25_scores)), float(max(bm25_scores))
            denom = (bm_max - bm_min) or 1.0
            bm25_norm = [(s - bm_min) / denom for s in bm25_scores]
        else:
            bm25_norm = [0.0] * len(raw_results)

        alpha = 0.7
        combined = [
            (i, alpha * raw_results[i]['similarity'] + (1 - alpha) * bm25_norm[i])
            for i in range(len(raw_results))
        ]
        combined.sort(key=lambda x: x[1], reverse=True)
        top_indices = [i for i, _ in combined[:top_k]]
        top = [raw_results[i] for i in top_indices]
        formatted: List[Dict[str, Any]] = []
        for r in top:
            md = r['metadata']
            formatted.append({
                'title': md.get('title'),
                'price': md.get('price'),
                'url': md.get('url')
            })
        return formatted
    
    def search_by_category(self, category: str, top_k: int = 5) -> List[Dict]:
        if not self.vector_db:
            raise ValueError("Vector database not initialized")
        
        category_embedding = self.embedding_generator.generate_single_embedding(category)
        results = self.vector_db.search(category_embedding, top_k=len(self.vector_db.embeddings))
        category_results = [
            result for result in results
            if str(result['metadata'].get('category', '')).lower() == category.lower()
        ][:top_k]
        
        logger.info(f"Category search completed. Found {len(category_results)} results for category: '{category}'")
        
        return category_results
    
    def search_by_price_range(self, min_price: float, max_price: float, 
                             top_k: int = 5) -> List[Dict]:
        if not self.vector_db:
            raise ValueError("Vector database not initialized")
        
        price_filtered = [
            (i, metadata) for i, metadata in enumerate(self.vector_db.metadata)
            if isinstance(metadata.get('price'), (int, float)) and min_price <= metadata['price'] <= max_price
        ]
        
        if not price_filtered:
            return []
        
        price_filtered.sort(key=lambda x: x[1]['price'])
        
        results = []
        for i, metadata in price_filtered[:top_k]:
            results.append({
                'id': self.vector_db.ids[i],
                'metadata': metadata,
                'similarity': 1.0
            })
        
        logger.info(f"Price range search completed. Found {len(results)} results for price range: ${min_price}-${max_price}")
        
        return results
    
    def get_recommendations(self, product_id: int, top_k: int = 5) -> List[Dict]:
        if not self.vector_db:
            raise ValueError("Vector database not initialized")
        
        try:
            product_idx = self.vector_db.ids.index(product_id)
        except ValueError:
            logger.error(f"Product with ID {product_id} not found")
            return []
        
        product_embedding = self.vector_db.embeddings[product_idx]
        all_results = self.vector_db.search(product_embedding, top_k=len(self.vector_db.embeddings))
        recommendations = [
            result for result in all_results
            if result['id'] != product_id
        ][:top_k]
        
        logger.info(f"Generated {len(recommendations)} recommendations for product {product_id}")
        
        return recommendations
    
    def format_search_results(self, results: List[Dict]) -> pd.DataFrame:
        if not results:
            return pd.DataFrame()
        
        formatted_data = []
        for result in results:
            metadata = result['metadata']
            formatted_data.append({
                'id': result['id'],
                'title': metadata.get('title'),
                'description': metadata.get('description'),
                'category': metadata.get('category'),
                'price': metadata.get('price'),
                'url': metadata.get('url'),
                'similarity_score': result['similarity']
            })
        
        df = pd.DataFrame(formatted_data)
        return df.sort_values('similarity_score', ascending=False)


class SearchAPI:
    def __init__(self, vector_db: VectorDatabase):
        self.searcher = ProductSearcher(vector_db)
    
    def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        results = self.searcher.search_products(query, top_k=top_k)
        formatted_results = self.searcher.format_search_results(results)
        
        return {
            'query': query,
            'total_results': len(results),
            'results': formatted_results.to_dict('records') if not formatted_results.empty else []
        }
    
    def get_product_info(self, product_id: int) -> Optional[Dict]:
        if not self.searcher.vector_db:
            return None
        
        try:
            product_idx = self.searcher.vector_db.ids.index(product_id)
            return self.searcher.vector_db.metadata[product_idx]
        except ValueError:
            return None


def main():
    import sys
    from embed_and_load import ProductEmbedder
    from ingest import DataIngester

    embedder = ProductEmbedder()

    if not getattr(embedder, 'use_pinecone', False):
        ingester = DataIngester()
        products_df = ingester.load_products()
        clean_df = ingester.preprocess_data(products_df)
        vector_db = embedder.embed_products(clean_df)
    else:
        vector_db = embedder.vector_db

    searcher = ProductSearcher(vector_db)

    query = " ".join(sys.argv[1:]).strip()
    if not query:
        query = input("Enter search query (e.g., 'linen summer dress under $300'): ").strip()

    results = searcher.simple_search(query, top_k=5)
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['title']} (${r['price']}) -> {r['url']}")

    return results


if __name__ == "__main__":
    main()
