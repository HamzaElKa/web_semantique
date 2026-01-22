from __future__ import annotations

from dataclasses import dataclass
import os


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


@dataclass(frozen=True)
class Settings:
    # Endpoints
    DBPEDIA_ENDPOINT: str = os.getenv("DBPEDIA_ENDPOINT", "https://dbpedia.org/sparql").strip()
    WIKIDATA_ENDPOINT: str = os.getenv("WIKIDATA_ENDPOINT", "https://query.wikidata.org/sparql").strip()
    HAL_ENDPOINT: str = os.getenv("HAL_ENDPOINT", "https://sparql.archives-ouvertes.fr/sparql").strip()

    # IA Générative (OpenAI / Mistral / Ollama)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "ollama").strip()

    # Default choice
    DEFAULT_ENDPOINT: str = os.getenv("DEFAULT_ENDPOINT", "dbpedia").strip().lower()  # "dbpedia" or "wikidata"

    # Guard rails
    HTTP_TIMEOUT_S: float = _get_float("HTTP_TIMEOUT_S", 15.0)
    MAX_LIMIT: int = _get_int("MAX_LIMIT", 200)
    DEFAULT_LIMIT: int = _get_int("DEFAULT_LIMIT", 50)

    # Simple cache
    CACHE_TTL_S: int = _get_int("CACHE_TTL_S", 900)  # 15 min
    CACHE_MAX_ITEMS: int = _get_int("CACHE_MAX_ITEMS", 2000)

    # CORS (comma-separated list), optional
    # Example: "http://localhost:5500,http://127.0.0.1:5500"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "").strip()


def _normalize_settings(s: Settings) -> Settings:
    # sanitize default endpoint
    endpoint = s.DEFAULT_ENDPOINT
    if endpoint not in ("dbpedia", "wikidata"):
        endpoint = "dbpedia"

    # sanitize limits
    max_limit = max(1, s.MAX_LIMIT)
    default_limit = min(max(1, s.DEFAULT_LIMIT), max_limit)

    # sanitize timeout
    timeout = s.HTTP_TIMEOUT_S
    if timeout <= 0:
        timeout = 15.0

    # rebuild frozen dataclass with corrected values
    return Settings(
        DBPEDIA_ENDPOINT=s.DBPEDIA_ENDPOINT,
        WIKIDATA_ENDPOINT=s.WIKIDATA_ENDPOINT,
        HAL_ENDPOINT=s.HAL_ENDPOINT,
        OPENAI_API_KEY=s.OPENAI_API_KEY,
        DEFAULT_ENDPOINT=endpoint,
        HTTP_TIMEOUT_S=timeout,
        MAX_LIMIT=max_limit,
        DEFAULT_LIMIT=default_limit,
        CACHE_TTL_S=max(1, s.CACHE_TTL_S),
        CACHE_MAX_ITEMS=max(1, s.CACHE_MAX_ITEMS),
        CORS_ORIGINS=s.CORS_ORIGINS,
    )


settings = _normalize_settings(Settings())