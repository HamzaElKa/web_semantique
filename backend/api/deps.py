from __future__ import annotations
from api.config import settings
from services.cache import TTLCache
from services.sparql_client import SparqlClient

_cache = TTLCache(ttl_seconds=settings.CACHE_TTL_S, max_items=settings.CACHE_MAX_ITEMS)
_sparql = SparqlClient(cache=_cache)

def get_sparql_client() -> SparqlClient:
    return _sparql
