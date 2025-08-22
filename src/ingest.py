import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Any
from schemas import REQUIRED_PRODUCT_COLUMNS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataIngester:
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        
    def load_products(self, filename: str = "products.csv") -> pd.DataFrame:
        file_path = self.data_dir / filename
        
        try:
            logger.info(f"Loading products from {file_path}")
            df = pd.read_csv(file_path)
            logger.info(f"Successfully loaded {len(df)} products")
            return df
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def validate_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        required_columns = REQUIRED_PRODUCT_COLUMNS
        missing_columns = [c for c in required_columns if c not in df.columns]

        validation_results = {
            "total_rows": len(df),
            "missing_values": df.isnull().sum().to_dict(),
            "duplicates": df.duplicated().sum(),
            "data_types": df.dtypes.to_dict(),
            "required_columns_present": len(missing_columns) == 0,
            "missing_columns": missing_columns
        }
        
        logger.info("Data validation completed")
        logger.info(f"Total rows: {validation_results['total_rows']}")
        logger.info(f"Missing values: {validation_results['missing_values']}")
        logger.info(f"Duplicates: {validation_results['duplicates']}")
        
        return validation_results
    
    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in REQUIRED_PRODUCT_COLUMNS:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        df_clean = df.drop_duplicates().copy()

        df_clean["category"] = (
            df_clean["category"].astype(str).str.strip().str.title()
        )
        df_clean["title"] = df_clean["title"].astype(str).str.strip()
        df_clean["description"] = df_clean["description"].astype(str).str.strip()
        df_clean["url"] = df_clean["url"].astype(str).str.strip()

        df_clean["id"] = pd.to_numeric(df_clean["id"], errors="coerce").astype("Int64")
        df_clean["price"] = pd.to_numeric(df_clean["price"], errors="coerce")

        df_clean = df_clean.dropna(subset=["id", "title", "category", "price", "url"]).copy()

        df_clean["id"] = df_clean["id"].astype(int)

        before = len(df_clean)
        df_clean = df_clean.drop_duplicates(subset=["id"], keep="first")
        after = len(df_clean)

        logger.info(f"Preprocessing completed. Cleaned {len(df)} -> {len(df_clean)} rows (removed {before - after} duplicate IDs)")

        df_clean = df_clean[REQUIRED_PRODUCT_COLUMNS]

        return df_clean


def main():
    ingester = DataIngester()
    
    try:
        products_df = ingester.load_products()
        validation_results = ingester.validate_data(products_df)
        clean_df = ingester.preprocess_data(products_df)
        print("Data ingestion completed successfully!")
        print(f"Loaded {len(clean_df)} products")
        
        return clean_df
        
    except Exception as e:
        logger.error(f"Data ingestion failed: {e}")
        raise


if __name__ == "__main__":
    main()
