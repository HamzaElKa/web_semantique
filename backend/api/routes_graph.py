from __future__ import annotations
from typing import Dict, List
from fastapi import APIRouter, Depends, Query
from api.schemas import GraphResponse, ApiMeta, EndpointName
from api.config import settings
from services.sparql_client import SparqlClient
from services.normalize import sparql_json_to_rows

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("", response_model=GraphResponse)
async def graph(
    seed: str = Query(..., description="Seed entity URI"),
    depth: int = Query(1, ge=1, le=2),
    endpoint: EndpointName = Query(settings.DEFAULT_ENDPOINT),
    limit: int = Query(80, ge=1, le=settings.MAX_LIMIT),
    sparql: SparqlClient = Depends(lambda: __import__("api.deps").deps.get_sparql_client()),
):
    seed_uri = seed.replace('"', '\\"')

    # 1-hop neighbors (keep simple; analysis module can build bigger)
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?s ?sLabel ?p ?pLabel ?o ?oLabel WHERE {{
      BIND(<{seed_uri}> AS ?s)
      ?s ?p ?o .
      OPTIONAL {{ ?s rdfs:label ?sLabel . FILTER(lang(?sLabel) IN ("en","fr")) }}
      OPTIONAL {{ ?p rdfs:label ?pLabel . FILTER(lang(?pLabel) IN ("en","fr")) }}
      OPTIONAL {{ ?o rdfs:label ?oLabel . FILTER(lang(?oLabel) IN ("en","fr")) }}
      FILTER(isIRI(?o))
    }}
    """

    data = await sparql.query(query=query, endpoint=endpoint, limit=limit, use_cache=True)
    rows = sparql_json_to_rows(data)

    nodes_map: Dict[str, Dict] = {}
    edges: List[Dict] = []

    def add_node(uri: str, label: str | None):
        if uri not in nodes_map:
            nodes_map[uri] = {"id": uri, "label": label or uri}

    for r in rows:
        s = r.get("s")
        o = r.get("o")
        pLabel = r.get("pLabel") or r.get("p") or ""
        sLabel = r.get("sLabel") or s
        oLabel = r.get("oLabel") or o
        if not s or not o:
            continue
        add_node(s, sLabel)
        add_node(o, oLabel)
        edges.append({"source": s, "target": o, "label": pLabel})

    return GraphResponse(
        meta=ApiMeta(endpoint=endpoint, limit=limit, cached=False),
        seed_uri=seed,
        depth=depth,
        nodes=list(nodes_map.values()),
        edges=edges,
    )
