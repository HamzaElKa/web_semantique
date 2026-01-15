from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from api.schemas import EntityResponse, ApiMeta, EndpointName
from api.config import settings
from api.deps import get_sparql_client
from services.sparql_client import SparqlClient
from services.normalize import sparql_json_to_rows

router = APIRouter(prefix="/entity", tags=["entity"])


def _validate_uri(u: str) -> str:
    u = (u or "").strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        raise HTTPException(status_code=400, detail="id must be a valid http(s) URI")
    # Very small hardening to avoid breaking the IRI injection
    if any(x in u for x in ["<", ">", "{", "}", '"', "'"]):
        raise HTTPException(status_code=400, detail="id contains invalid characters")
    return u


@router.get("", response_model=EntityResponse)
async def entity(
    id: str = Query(..., description="Entity URI (http(s) IRI)"),
    endpoint: EndpointName = Query(settings.DEFAULT_ENDPOINT),
    limit: int = Query(settings.DEFAULT_LIMIT, ge=1, le=settings.MAX_LIMIT),
    sparql: SparqlClient = Depends(get_sparql_client),
):
    uri = _validate_uri(id)

    if endpoint == "dbpedia":
        query = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?p ?pLabel ?o ?oLabel WHERE {{
  BIND(<{uri}> AS ?s)
  ?s ?p ?o .

  OPTIONAL {{ ?p rdfs:label ?pLabel . FILTER(lang(?pLabel) IN ("en","fr")) }}
  OPTIONAL {{ ?o rdfs:label ?oLabel . FILTER(lang(?oLabel) IN ("en","fr")) }}
}}
        """.strip()
    else:
        # Wikidata: keep it generic, but add missing PREFIX rdfs
        query = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?p ?pLabel ?o ?oLabel WHERE {{
  BIND(<{uri}> AS ?s)
  ?s ?p ?o .

  OPTIONAL {{ ?p rdfs:label ?pLabel . FILTER(lang(?pLabel) IN ("en","fr")) }}
  OPTIONAL {{ ?o rdfs:label ?oLabel . FILTER(lang(?oLabel) IN ("en","fr")) }}
}}
        """.strip()

    data = await sparql.query(query=query, endpoint=endpoint, limit=limit, use_cache=True)
    rows = sparql_json_to_rows(data)

    facts: Dict[str, List[Dict[str, Any]]] = {}
    neighbors: List[Dict[str, Any]] = []
    label: Optional[str] = None

    for r in rows:
        p = r.get("p")
        o = r.get("o")
        p_label = r.get("pLabel") or p
        o_label = r.get("oLabel") or o

        if not p or not o:
            continue

        # Try to pick entity label from rdfs:label (common on DBpedia)
        if isinstance(p, str) and p.endswith("/label") and isinstance(o_label, str):
            label = o_label

        # Store facts (cap per predicate)
        key = str(p_label)
        facts.setdefault(key, [])
        if len(facts[key]) < 10:
            facts[key].append({"value": o, "label": o_label})

        # Neighbors: objects that look like URIs
        if isinstance(o, str) and (o.startswith("http://") or o.startswith("https://")):
            neighbors.append({"predicate": key, "uri": o, "label": o_label})

    return EntityResponse(
        meta=ApiMeta(endpoint=endpoint, limit=limit, cached=False),
        uri=id,
        label=label,
        facts=facts,
        neighbors=neighbors[:200],
    )
