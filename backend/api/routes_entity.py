from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from api.schemas import EntityResponse, ApiMeta, EndpointName
from api.config import settings
from services.sparql_client import SparqlClient
from services.normalize import sparql_json_to_rows

router = APIRouter(prefix="/entity", tags=["entity"])

@router.get("", response_model=EntityResponse)
async def entity(
    id: str = Query(..., description="Entity URI"),
    endpoint: EndpointName = Query(settings.DEFAULT_ENDPOINT),
    limit: int = Query(settings.DEFAULT_LIMIT, ge=1, le=settings.MAX_LIMIT),
    sparql: SparqlClient = Depends(lambda: __import__("api.deps").deps.get_sparql_client()),
):
    uri = id.replace('"', '\\"')

    if endpoint == "dbpedia":
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dbo:  <http://dbpedia.org/ontology/>
        SELECT ?p ?pLabel ?o ?oLabel WHERE {{
          BIND(<{uri}> AS ?s)
          ?s ?p ?o .

          OPTIONAL {{ ?p rdfs:label ?pLabel . FILTER(lang(?pLabel) IN ("en","fr")) }}
          OPTIONAL {{ ?o rdfs:label ?oLabel . FILTER(lang(?oLabel) IN ("en","fr")) }}
        }}
        """
    else:
        query = f"""
        SELECT ?p ?pLabel ?o ?oLabel WHERE {{
          BIND(<{uri}> AS ?s)
          ?s ?p ?o .
          OPTIONAL {{ ?p rdfs:label ?pLabel . FILTER(lang(?pLabel) IN ("en","fr")) }}
          OPTIONAL {{ ?o rdfs:label ?oLabel . FILTER(lang(?oLabel) IN ("en","fr")) }}
        }}
        """

    data = await sparql.query(query=query, endpoint=endpoint, limit=limit, use_cache=True)
    rows = sparql_json_to_rows(data)

    facts = {}
    neighbors = []
    label = None

    for r in rows:
        p = r.get("p")
        o = r.get("o")
        pLabel = r.get("pLabel") or p
        oLabel = r.get("oLabel") or o

        if not p or not o:
            continue

        # Try to pick entity label from rdfs:label
        if str(p).endswith("label") and isinstance(oLabel, str):
            label = oLabel

        # Store facts (keep a short list per predicate)
        facts.setdefault(pLabel, [])
        if len(facts[pLabel]) < 10:
            facts[pLabel].append({"value": o, "label": oLabel})

        # Neighbor candidates: object that looks like URI
        if isinstance(o, str) and o.startswith("http"):
            neighbors.append({"predicate": pLabel, "uri": o, "label": oLabel})

    return EntityResponse(
        meta=ApiMeta(endpoint=endpoint, limit=limit, cached=False),
        uri=id,
        label=label,
        facts=facts,
        neighbors=neighbors[: min(len(neighbors), 200)],
    )
