from __future__ import annotations

from typing import Dict, Literal, Optional
import asyncio
import hashlib

import httpx
from fastapi import HTTPException

from api.config import settings
from services.cache import TTLCache

# DBpedia-only project
EndpointName = Literal["dbpedia"]


class SparqlClient:
    """
    Robust SPARQL client for DBpedia.

    - Uses GET with explicit 'format=application/sparql-results+json'
    - Guardrails: LIMIT cap, timeouts, retries, cache.
    - DBpedia can sometimes return an HTML "maintenance" page with HTTP 200.
    """

    def __init__(self, cache: TTLCache):
        self.cache = cache

    @staticmethod
    def _endpoint_url() -> str:
        return settings.DBPEDIA_ENDPOINT

    @staticmethod
    def _enforce_limit(query: str, limit: int) -> str:
        # If query already has LIMIT, keep it as-is. Otherwise append LIMIT.
        q_upper = query.upper()
        if "LIMIT" in q_upper:
            return query.strip()
        return query.strip() + f"\nLIMIT {limit}\n"

    @staticmethod
    def _cache_key(limit: int, final_query: str) -> str:
        h = hashlib.sha256(final_query.encode("utf-8")).hexdigest()
        return f"dbpedia::{limit}::{h}"

    @staticmethod
    def _is_maintenance_html(resp: httpx.Response) -> bool:
        ct = (resp.headers.get("content-type") or "").lower()
        if "text/html" not in ct:
            return False
        body = (resp.text or "").lower()
        return ("under maintenance" in body) or ("web site under maintenance" in body)

    @staticmethod
    def _should_retry(status_code: int) -> bool:
        return status_code in (429, 500, 502, 503, 504)

    @staticmethod
    def _retry_after_seconds(resp: httpx.Response, default_s: float) -> float:
        ra = resp.headers.get("retry-after")
        if not ra:
            return default_s
        try:
            return float(ra)
        except Exception:
            return default_s

    async def _request_sparql(self, final_query: str) -> Dict:
        url = self._endpoint_url()

        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "4IF-WS-Foot-Explorer/1.0 (INSA Lyon; contact: student)",
        }

        timeout = httpx.Timeout(settings.HTTP_TIMEOUT_S, connect=settings.HTTP_TIMEOUT_S)

        params = {
            "query": final_query,
            "format": "application/sparql-results+json",
        }

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            trust_env=True,  # Windows proxy corporate compatible
        ) as client:
            last_status: Optional[int] = None

            for attempt in range(1, 4):  # 3 attempts
                try:
                    resp = await client.get(url, params=params, headers=headers)

                except httpx.TimeoutException:
                    if attempt == 3:
                        raise HTTPException(status_code=504, detail="SPARQL endpoint timeout (dbpedia)")
                    await asyncio.sleep(0.4 * attempt)
                    continue

                except httpx.RequestError as e:
                    raise HTTPException(status_code=502, detail=f"SPARQL endpoint error (dbpedia): {str(e)}")

                # DBpedia may return 200 with HTML maintenance page
                if resp.status_code == 200 and self._is_maintenance_html(resp):
                    last_status = 503
                    if attempt == 3:
                        raise HTTPException(status_code=503, detail="DBpedia under maintenance")
                    await asyncio.sleep(0.7 * attempt)
                    continue

                # Retryable HTTP codes
                if self._should_retry(resp.status_code):
                    last_status = resp.status_code
                    if attempt == 3:
                        raise HTTPException(status_code=resp.status_code, detail=f"dbpedia returned {resp.status_code}")
                    wait_s = self._retry_after_seconds(resp, default_s=0.6 * (2 ** (attempt - 1)))
                    await asyncio.sleep(min(wait_s, 5.0))
                    continue

                if resp.status_code != 200:
                    raise HTTPException(status_code=resp.status_code, detail=f"dbpedia returned {resp.status_code}")

                try:
                    return resp.json()
                except Exception:
                    ct = resp.headers.get("content-type", "")
                    raise HTTPException(
                        status_code=502,
                        detail=f"dbpedia returned non-JSON response (Content-Type: {ct})",
                    )

            raise HTTPException(status_code=502, detail=f"dbpedia request failed ({last_status})")

    async def query(self, query: str, endpoint: EndpointName, limit: int, use_cache: bool = True) -> Dict:
        # Keep signature compatible with the rest of the codebase (endpoint is always 'dbpedia')
        if endpoint != "dbpedia":
            raise HTTPException(status_code=400, detail="Only DBpedia endpoint is supported")

        if limit <= 0:
            raise HTTPException(status_code=400, detail="limit must be > 0")
        if limit > settings.MAX_LIMIT:
            limit = settings.MAX_LIMIT

        final_query = self._enforce_limit(query, limit)

        cache_key = self._cache_key(limit, final_query)
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        data = await self._request_sparql(final_query=final_query)

        if use_cache:
            self.cache.set(cache_key, data)

        return data
