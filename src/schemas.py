from __future__ import annotations

from typing import List
from pathlib import Path
from pydantic import BaseModel, HttpUrl, Field
import json


SCHEMA_VERSION: str = "1.0.0"

REQUIRED_PRODUCT_COLUMNS: List[str] = [
	"id",
	"category",
	"title",
	"description",
	"price",
	"url",
]


class Product(BaseModel):

	id: int = Field(..., description="Unique product identifier")
	category: str = Field(..., description="Top-level product category")
	title: str = Field(..., description="Product title or name")
	description: str = Field(..., description="Product description")
	price: float = Field(..., ge=0, description="Product price (non-negative)")
	url: HttpUrl = Field(..., description="Product URL (HTTP/HTTPS)")


def product_dataframe_columns() -> List[str]:
	return list(REQUIRED_PRODUCT_COLUMNS)


def generate_json_schema() -> dict:
	schema = Product.model_json_schema()
	schema.setdefault("$id", "https://example.com/schemas/product.schema.json")
	schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
	schema.setdefault("title", "Product")
	schema.setdefault("version", SCHEMA_VERSION)
	return schema


def save_json_schema(target_path: str) -> None:
	path = Path(target_path)
	path.parent.mkdir(parents=True, exist_ok=True)
	schema = generate_json_schema()
	with path.open("w", encoding="utf-8") as f:
		json.dump(schema, f, indent=2)


if __name__ == "__main__":
	save_json_schema("docs/product.schema.json")


