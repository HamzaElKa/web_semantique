from __future__ import annotations

from typing import Dict, Literal
import httpx
from fastapi import HTTPException

from api.config import settings
from services.cache import TTLCache

EndpointName = Literal["dbpedia", "wikidata"]


class SparqlClient:
    """
    Robust SPARQL client for DBpedia + Wikidata.

    - DBpedia: GET is usually OK, but can return an HTML "maintenance" page.
    - Wikidata: should be queried with POST + explicit User-Agent.
    - Guardrails: LIMIT cap, timeouts, retries, cache.
    - Optional fallback: if DBpedia fails (timeout/502/503/504/maintenance), retry once on Wikidata.
    """

    def __init__(self, cache: TTLCache):
        self.cache = cache

    def _endpoint_url(self, endpoint: EndpointName) -> str:
        if endpoint == "dbpedia":
            return settings.DBPEDIA_ENDPOINT
        if endpoint == "wikidata":
            return settings.WIKIDATA_ENDPOINT
        raise ValueError("Unknown endpoint")

    def _enforce_limit(self, query: str, limit: int) -> str:
        # If query already has LIMIT, keep it as-is. Otherwise append LIMIT.
        # (We still cap limit at route-level + MAX_LIMIT here.)
        q_upper = query.upper()
        if "LIMIT" in q_upper:
            return query
        return query.strip() + f"\nLIMIT {limit}\n"

    @staticmethod
    def _is_maintenance_html(resp: httpx.Response) -> bool:
        ct = (resp.headers.get("content-type") or "").lower()
        if "text/html" not in ct:
            return False
        body = (resp.text or "").lower()
        return ("under maintenance" in body) or ("web site under maintenance" in body)

    async def _request_sparql(self, endpoint: EndpointName, final_query: str) -> Dict:
        url = self._endpoint_url(endpoint)

        # Important headers for Wikidata. Put a real contact if possible.
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "4IF-WS-Foot-Explorer/1.0 (INSA Lyon; contact: your-email@insa-lyon.fr)",
        }

        timeout = httpx.Timeout(settings.HTTP_TIMEOUT_S, connect=settings.HTTP_TIMEOUT_S)

        # Wikidata often prefers POST (and can 403 for heavy GET usage).
        # DBpedia: GET is fine.
        params = {"query": final_query, "format": "json"}
        data = {"query": final_query}

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                trust_env=True,  # use system proxy if any (common on Windows)
            ) as client:
                # Small retry loop for timeouts (network hiccups / endpoint load)
                last_exc: Exception | None = None
                for attempt in range(3):
                    try:
                        if endpoint == "wikidata":
                            resp = await client.post(
                                url,
                                data=data,
                                headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                            )
                        else:
                            resp = await client.get(url, params=params, headers=headers)

                        break
                    except httpx.TimeoutException as e:
                        last_exc = e
                        if attempt == 2:
                            raise
                else:
                    # should never hit
                    raise httpx.TimeoutException("timeout")

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail=f"SPARQL endpoint timeout ({endpoint})")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"SPARQL endpoint error ({endpoint}): {str(e)}")

        # DBpedia may return 200 with an HTML maintenance page
        if endpoint == "dbpedia" and self._is_maintenance_html(resp):
            raise HTTPException(status_code=503, detail="DBpedia under maintenance")

        # Wikidata may return 403 if request is considered abusive / UA missing / query too broad
        if resp.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden from {endpoint} (try POST/stricter query/User-Agent)",
            )

        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"{endpoint} returned {resp.status_code}")

        # Sometimes an endpoint returns non-JSON even if 200
        try:
            return resp.json()
        except Exception:
            ct = resp.headers.get("content-type", "")
            raise HTTPException(status_code=502, detail=f"{endpoint} returned non-JSON response (Content-Type: {ct})")

    async def query(self, query: str, endpoint: EndpointName, limit: int, use_cache: bool = True) -> Dict:
        if limit <= 0:
            raise HTTPException(status_code=400, detail="limit must be > 0")
        if limit > settings.MAX_LIMIT:
            limit = settings.MAX_LIMIT

        final_query = self._enforce_limit(query, limit)

        cache_key = f"{endpoint}::{limit}::{hash(final_query)}"
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Primary attempt
        try:
            data = await self._request_sparql(endpoint=endpoint, final_query=final_query)
        except HTTPException as e:
            # Optional fallback: if DBpedia fails, retry once on Wikidata
            if endpoint == "dbpedia" and e.status_code in (502, 503, 504):
                data = await self._request_sparql(endpoint="wikidata", final_query=final_query)
                endpoint_used = "wikidata"
                # cache under both keys (optional). Keep it simple: cache under requested endpoint.
            else:
                raise

        if use_cache:
            self.cache.set(cache_key, data)

        return data
