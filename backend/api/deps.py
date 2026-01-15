from __future__ import annotations

from api.config import settings
from services.cache import TTLCache
from services.sparql_client import SparqlClient


# Singletons (shared across requests)
_cache: TTLCache = TTLCache(
    ttl_seconds=settings.CACHE_TTL_S,
    max_items=settings.CACHE_MAX_ITEMS,
)

_sparql: SparqlClient = SparqlClient(cache=_cache)


def get_sparql_client() -> SparqlClient:
    """
    Dependency provider for a shared SparqlClient instance.
    """
    return _sparql


def get_cache() -> TTLCache:
    """
    Optional dependency provider for cache (useful for debugging/tests).
    """
    return _cache
