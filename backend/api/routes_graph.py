from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from api.schemas import GraphResponse, ApiMeta, EndpointName
from api.config import settings
from api.deps import get_sparql_client
from services.sparql_client import SparqlClient
from services.normalize import sparql_json_to_rows

router = APIRouter(prefix="/graph", tags=["graph"])


def _validate_uri(u: str) -> str:
    u = (u or "").strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        raise HTTPException(status_code=400, detail="seed must be a valid http(s) URI")
    if any(x in u for x in ["<", ">", "{", "}", '"', "'"]):
        raise HTTPException(status_code=400, detail="seed contains invalid characters")
    return u


def _add_node(nodes_map: Dict[str, Dict[str, Any]], uri: str, label: Optional[str]) -> None:
    if uri not in nodes_map:
        nodes_map[uri] = {"id": uri, "label": label or uri}


@router.get("", response_model=GraphResponse)
async def graph(
    seed: str = Query(..., description="Seed entity URI (http(s))"),
    depth: int = Query(1, ge=1, le=2, description="1 or 2 hops (2 hops may be heavier)"),
    endpoint: EndpointName = Query(settings.DEFAULT_ENDPOINT),
    limit: int = Query(80, ge=1, le=settings.MAX_LIMIT),
    sparql: SparqlClient = Depends(get_sparql_client),
):
    seed_uri = _validate_uri(seed)

    # 1-hop query
    query_1 = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?s ?sLabel ?p ?pLabel ?o ?oLabel WHERE {{
  BIND(<{seed_uri}> AS ?s)
  ?s ?p ?o .

  FILTER(isIRI(?o))

  OPTIONAL {{ ?s rdfs:label ?sLabel . FILTER(lang(?sLabel) IN ("en","fr")) }}
  OPTIONAL {{ ?p rdfs:label ?pLabel . FILTER(lang(?pLabel) IN ("en","fr")) }}
  OPTIONAL {{ ?o rdfs:label ?oLabel . FILTER(lang(?oLabel) IN ("en","fr")) }}
}}
""".strip()

    data1 = await sparql.query(query=query_1, endpoint=endpoint, limit=limit, use_cache=True)
    rows1 = sparql_json_to_rows(data1)

    nodes_map: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    # Build 1-hop graph
    one_hop_targets: List[str] = []
    for r in rows1:
        s = r.get("s")
        o = r.get("o")
        if not s or not o:
            continue

        p_label = r.get("pLabel") or r.get("p") or ""
        s_label = r.get("sLabel") or s
        o_label = r.get("oLabel") or o

        _add_node(nodes_map, s, s_label)
        _add_node(nodes_map, o, o_label)
        edges.append({"source": s, "target": o, "label": p_label})

        if isinstance(o, str) and (o.startswith("http://") or o.startswith("https://")):
            one_hop_targets.append(o)

    # Optional 2-hop expansion (lightweight): expand a small subset of targets
    if depth == 2 and one_hop_targets:
        # Keep only a small number of targets to avoid exploding requests
        # (and keep within demo constraints)
        max_targets = 15
        targets = one_hop_targets[:max_targets]

        values = " ".join(f"<{t}>" for t in targets)

        query_2 = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?s ?sLabel ?p ?pLabel ?o ?oLabel WHERE {{
  VALUES ?s {{ {values} }}
  ?s ?p ?o .
  FILTER(isIRI(?o))

  OPTIONAL {{ ?s rdfs:label ?sLabel . FILTER(lang(?sLabel) IN ("en","fr")) }}
  OPTIONAL {{ ?p rdfs:label ?pLabel . FILTER(lang(?pLabel) IN ("en","fr")) }}
  OPTIONAL {{ ?o rdfs:label ?oLabel . FILTER(lang(?oLabel) IN ("en","fr")) }}
}}
""".strip()

        # Use a smaller limit for 2-hop to avoid huge payload
        limit2 = min(200, settings.MAX_LIMIT)
        data2 = await sparql.query(query=query_2, endpoint=endpoint, limit=limit2, use_cache=True)
        rows2 = sparql_json_to_rows(data2)

        for r in rows2:
            s = r.get("s")
            o = r.get("o")
            if not s or not o:
                continue

            p_label = r.get("pLabel") or r.get("p") or ""
            s_label = r.get("sLabel") or s
            o_label = r.get("oLabel") or o

            _add_node(nodes_map, s, s_label)
            _add_node(nodes_map, o, o_label)
            edges.append({"source": s, "target": o, "label": p_label})

    # Cap edges to keep response small
    if len(edges) > 2000:
        edges = edges[:2000]

    return GraphResponse(
        meta=ApiMeta(endpoint=endpoint, limit=limit, cached=False),
        seed_uri=seed_uri,
        depth=depth,
        nodes=list(nodes_map.values()),
        edges=edges,
    )
