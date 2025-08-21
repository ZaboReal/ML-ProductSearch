import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from schemas import REQUIRED_PRODUCT_COLUMNS
import json
import logging
from pathlib import Path
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.warning(f"Configuration file {config_path} not found, using defaults")
        return get_default_config()
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    return {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "data_dir": "data",
        "embeddings_file": "data/product_embeddings.pkl",
        "max_search_results": 10,
        "min_similarity_threshold": 0.3,
        "logging_level": "INFO"
    }


def save_config(config: Dict[str, Any], config_path: str = "config.json"):
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")


def clean_text(text: str) -> str:
    if not text:
        return ""
    
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    return text


def calculate_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    if np.array_equal(vec1, vec2):
        return 1.0
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def format_price(price: float) -> str:
    return f"${price:.2f}"


def format_rating(rating: float) -> str:
    full_stars = int(rating)
    half_star = rating % 1 >= 0.5
    empty_stars = 5 - full_stars - (1 if half_star else 0)
    
    stars = "★" * full_stars
    if half_star:
        stars += "☆"
    stars += "☆" * empty_stars
    
    return f"{stars} ({rating:.1f})"


def validate_product_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    errors = []
    required_columns = REQUIRED_PRODUCT_COLUMNS
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {missing_columns}")
    
    if 'price' in df.columns and not pd.api.types.is_numeric_dtype(df['price']):
        errors.append("Price column must be numeric")
    
    critical_fields = ['title', 'description', 'url']
    for field in critical_fields:
        if field in df.columns and df[field].isnull().any():
            errors.append(f"Missing values found in {field} column")
    
    if 'price' in df.columns:
        if (df['price'] < 0).any():
            errors.append("Price values must be non-negative")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def create_search_summary(results: List[Dict]) -> Dict[str, Any]:
    if not results:
        return {
            'total_results': 0,
            'price_range': None,
            'categories': [],
            'avg_price': 0.0
        }

    prices = [result['metadata'].get('price') for result in results if isinstance(result['metadata'].get('price'), (int, float, np.floating))]
    categories = list({result['metadata'].get('category') for result in results if result['metadata'].get('category')})

    return {
        'total_results': len(results),
        'price_range': (min(prices), max(prices)) if prices else None,
        'categories': categories,
        'avg_price': float(np.mean(prices)) if prices else 0.0
    }


def export_results_to_csv(results: List[Dict], output_path: str):
    if not results:
        logger.warning("No results to export")
        return
    
    data = []
    for result in results:
        metadata = result['metadata']
        data.append({
            'id': result.get('id'),
            'title': metadata.get('title'),
            'description': metadata.get('description'),
            'category': metadata.get('category'),
            'price': metadata.get('price'),
            'url': metadata.get('url'),
            'similarity_score': result.get('similarity')
        })
    
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    logger.info(f"Results exported to {output_path}")


def export_results_to_json(results: List[Dict], output_path: str):
    if not results:
        logger.warning("No results to export")
        return
    
    export_data = {
        'timestamp': datetime.now().isoformat(),
        'total_results': len(results),
        'results': results
    }
    
    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    logger.info(f"Results exported to {output_path}")


def get_product_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    stats = {
        'total_products': len(df),
        'categories': df['category'].value_counts().to_dict() if 'category' in df.columns else {},
        'price_stats': {
            'min': float(df['price'].min()) if 'price' in df.columns and len(df) else None,
            'max': float(df['price'].max()) if 'price' in df.columns and len(df) else None,
            'mean': float(df['price'].mean()) if 'price' in df.columns and len(df) else None,
            'median': float(df['price'].median()) if 'price' in df.columns and len(df) else None
        }
    }
    
    return stats


def print_product_info(product: Dict[str, Any]):
    print(f"ID: {product['id']}")
    print(f"Title: {product['title']}")
    print(f"Description: {product['description']}")
    print(f"Category: {product['category']}")
    print(f"Price: {format_price(product['price'])}")
    print(f"URL: {product['url']}")
    print("-" * 50)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )
    
    logger.info(f"Logging configured with level: {log_level}")


def ensure_directory_exists(directory: str):
    Path(directory).mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured directory exists: {directory}")


def main():
    print("=== Utility Functions Demo ===\n")
    
    test_text = "  Hello, World!  This is a TEST.  "
    cleaned = clean_text(test_text)
    print(f"Original: '{test_text}'")
    print(f"Cleaned: '{cleaned}'\n")
    
    vec1 = np.array([1, 0, 0])
    vec2 = np.array([0, 1, 0])
    similarity = calculate_similarity(vec1, vec2)
    print(f"Similarity between [1,0,0] and [0,1,0]: {similarity}\n")
    
    print(f"Price formatting: {format_price(29.99)}")
    print(f"Rating formatting: {format_rating(4.3)}\n")
    
    print("Utility functions demo completed!")


if __name__ == "__main__":
    main()
