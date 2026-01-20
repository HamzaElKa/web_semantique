from __future__ import annotations

from typing import Dict, Literal, Optional
import asyncio
import hashlib

import httpx
from fastapi import HTTPException

from api.config import settings
from services.cache import TTLCache

EndpointName = Literal["dbpedia", "wikidata","hal"]


class SparqlClient:
    """
    Robust SPARQL client for DBpedia + Wikidata.

    - DBpedia: GET is usually OK, but can return an HTML "maintenance" page.
    - Wikidata: prefer POST + explicit User-Agent + Api-User-Agent.
    - Guardrails: LIMIT cap, timeouts, retries, cache.
    """

    def __init__(self, cache: TTLCache):
        self.cache = cache

    def _endpoint_url(self, endpoint: EndpointName) -> str:
        if endpoint == "dbpedia":
            return settings.DBPEDIA_ENDPOINT
        if endpoint == "wikidata":
            return settings.WIKIDATA_ENDPOINT
        if endpoint == "hal":
            return settings.HAL_ENDPOINT
        raise ValueError("Unknown endpoint")


    def _enforce_limit(self, query: str, limit: int) -> str:
        # If query already has LIMIT, keep it as-is. Otherwise append LIMIT.
        q_upper = query.upper()
        if "LIMIT" in q_upper:
            return query.strip()
        return query.strip() + f"\nLIMIT {limit}\n"

    @staticmethod
    def _cache_key(endpoint: EndpointName, limit: int, final_query: str) -> str:
        h = hashlib.sha256(final_query.encode("utf-8")).hexdigest()
        return f"{endpoint}::{limit}::{h}"

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

    async def _request_sparql(self, endpoint: EndpointName, final_query: str) -> Dict:
        url = self._endpoint_url(endpoint)

        # IMPORTANT: put a real contact mail if you can (teacher-friendly)
        base_headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "4IF-WS-Foot-Explorer/1.0 (INSA Lyon; contact: student)",
        }

        # Wikidata likes Api-User-Agent specifically
        if endpoint == "wikidata":
            base_headers["Api-User-Agent"] = base_headers["User-Agent"]

        timeout = httpx.Timeout(settings.HTTP_TIMEOUT_S, connect=settings.HTTP_TIMEOUT_S)

        # Prefer explicit format that yields SPARQL JSON
        # DBpedia: GET with query params
        # Wikidata: POST with x-www-form-urlencoded
        params_dbpedia = {
            "query": final_query,
            "format": "application/sparql-results+json",
        }
        data_wikidata = {
            "query": final_query,
            "format": "json",
        }

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            trust_env=True,  # Windows proxy corporate compatible
        ) as client:
            last_status: Optional[int] = None
            last_body_snippet: str = ""

            for attempt in range(1, 4):  # 3 attempts
                try:
                    if endpoint == "wikidata":
                        resp = await client.post(
                            url,
                            data=data_wikidata,
                            headers={**base_headers, "Content-Type": "application/x-www-form-urlencoded"},
                        )
                    else:
                        resp = await client.get(url, params=params_dbpedia, headers=base_headers)

                except httpx.TimeoutException:
                    if attempt == 3:
                        raise HTTPException(status_code=504, detail=f"SPARQL endpoint timeout ({endpoint})")
                    await asyncio.sleep(0.4 * attempt)
                    continue

                except httpx.RequestError as e:
                    # Network error (DNS/proxy/etc)
                    raise HTTPException(status_code=502, detail=f"SPARQL endpoint error ({endpoint}): {str(e)}")

                # DBpedia may return 200 with HTML maintenance page
                if endpoint == "dbpedia" and resp.status_code == 200 and self._is_maintenance_html(resp):
                    # treat as 503 and retry (maybe transient)
                    last_status = 503
                    last_body_snippet = "DBpedia under maintenance (HTML)"
                    if attempt == 3:
                        raise HTTPException(status_code=503, detail="DBpedia under maintenance")
                    await asyncio.sleep(0.7 * attempt)
                    continue

                # Retryable HTTP codes
                if self._should_retry(resp.status_code):
                    last_status = resp.status_code
                    last_body_snippet = (resp.text or "")[:200]

                    if attempt == 3:
                        # final failure
                        raise HTTPException(
                            status_code=resp.status_code,
                            detail=f"{endpoint} returned {resp.status_code}",
                        )

                    # exponential backoff (+ respect Retry-After if present)
                    wait_s = self._retry_after_seconds(resp, default_s=0.6 * (2 ** (attempt - 1)))
                    await asyncio.sleep(min(wait_s, 5.0))
                    continue

                # Non-retryable error
                if resp.status_code != 200:
                    raise HTTPException(status_code=resp.status_code, detail=f"{endpoint} returned {resp.status_code}")

                # Parse JSON
                try:
                    return resp.json()
                except Exception:
                    ct = resp.headers.get("content-type", "")
                    # Sometimes endpoints still return XML/RDF; give a clear message
                    raise HTTPException(
                        status_code=502,
                        detail=f"{endpoint} returned non-JSON response (Content-Type: {ct})",
                    )

            # Should never happen
            raise HTTPException(status_code=502, detail=f"{endpoint} request failed ({last_status}) {last_body_snippet}")

    async def query(self, query: str, endpoint: EndpointName, limit: int, use_cache: bool = True) -> Dict:
        if limit <= 0:
            raise HTTPException(status_code=400, detail="limit must be > 0")
        if limit > settings.MAX_LIMIT:
            limit = settings.MAX_LIMIT

        final_query = self._enforce_limit(query, limit)

        cache_key = self._cache_key(endpoint, limit, final_query)
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        data = await self._request_sparql(endpoint=endpoint, final_query=final_query)

        if use_cache:
            self.cache.set(cache_key, data)

        return data
