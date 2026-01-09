from __future__ import annotations
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    # Endpoints
    DBPEDIA_ENDPOINT: str = os.getenv("DBPEDIA_ENDPOINT", "https://dbpedia.org/sparql")
    WIKIDATA_ENDPOINT: str = os.getenv("WIKIDATA_ENDPOINT", "https://query.wikidata.org/sparql")

    # Default choice (you can switch later)
    DEFAULT_ENDPOINT: str = os.getenv("DEFAULT_ENDPOINT", "dbpedia")  # "dbpedia" or "wikidata"

    # Guard rails
    HTTP_TIMEOUT_S: float = float(os.getenv("HTTP_TIMEOUT_S", "15"))
    MAX_LIMIT: int = int(os.getenv("MAX_LIMIT", "200"))
    DEFAULT_LIMIT: int = int(os.getenv("DEFAULT_LIMIT", "50"))

    # Simple cache
    CACHE_TTL_S: int = int(os.getenv("CACHE_TTL_S", "900"))  # 15 min
    CACHE_MAX_ITEMS: int = int(os.getenv("CACHE_MAX_ITEMS", "2000"))

settings = Settings()