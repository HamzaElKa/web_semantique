from __future__ import annotations

from typing import List, Literal
from fastapi import APIRouter, Depends, Query

from api.schemas import SearchResponse, ApiMeta, SearchResultItem, EndpointName
from api.config import settings
from api.deps import get_sparql_client
from services.sparql_client import SparqlClient
from services.normalize import sparql_json_to_rows

router = APIRouter(prefix="/search", tags=["search"])

EntityType = Literal["player", "club", "stadium"]


def _wikidata_type_filter(entity_type: EntityType) -> str:
    # Wikidata entities (Q-ids) used for constraints
    # player: human + occupation association football player (Q937857)
    # club: association football club (Q476028) or subclass
    # stadium: stadium (Q483110) or subclass
    if entity_type == "player":
        return """
      ?uri wdt:P31 wd:Q5 .
      ?uri wdt:P106 wd:Q937857 .
        """.strip()
    if entity_type == "club":
        return """
      ?uri wdt:P31/wdt:P279* wd:Q476028 .
        """.strip()
    return """
      ?uri wdt:P31/wdt:P279* wd:Q483110 .
    """.strip()


def _clean_search_text(s: str) -> str:
    # Avoid breaking SPARQL strings
    s = (s or "").strip()
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", " ").replace("\r", " ")
    return s


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2),
    entity_type: EntityType = Query("player"),
    endpoint: EndpointName = Query(settings.DEFAULT_ENDPOINT),
    limit: int = Query(settings.DEFAULT_LIMIT, ge=1, le=settings.MAX_LIMIT),
    sparql: SparqlClient = Depends(get_sparql_client),
):
    q_escaped = _clean_search_text(q)

    if endpoint == "dbpedia":
        query = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dbo:  <http://dbpedia.org/ontology/>

SELECT ?uri ?label ?comment WHERE {{
  ?uri rdfs:label ?label .
  FILTER (lang(?label) IN ("en","fr")) .
  FILTER (CONTAINS(LCASE(STR(?label)), LCASE("{q_escaped}"))) .

  OPTIONAL {{
    ?uri rdfs:comment ?comment .
    FILTER (lang(?comment) IN ("en","fr")) .
  }}

  # light hints (not strict filters)
  { "OPTIONAL { ?uri dbo:team ?t . }" if entity_type == "player" else "" }
  { "OPTIONAL { ?uri dbo:ground ?g . }" if entity_type == "club" else "" }
  { "OPTIONAL { ?uri dbo:capacity ?cap . }" if entity_type == "stadium" else "" }
}}
        """.strip()

    else:
        # Wikidata: use mwapi EntitySearch (fast), then apply type constraints
        type_filter = _wikidata_type_filter(entity_type)

        # mwapi returns Q-ids; we build the full entity IRI into ?uri
        query = f"""
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX bd: <http://www.bigdata.com/rdf#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>

SELECT ?uri ?label ?comment WHERE {{
  SERVICE wikibase:mwapi {{
    bd:serviceParam wikibase:api "EntitySearch" .
    bd:serviceParam wikibase:search "{q_escaped}" .
    bd:serviceParam wikibase:language "en" .
    bd:serviceParam wikibase:limit {min(limit, 20)} .
    ?item wikibase:apiOutputItem mwapi:item .
  }}

  BIND(IRI(CONCAT("http://www.wikidata.org/entity/", STR(?item))) AS ?uri)

  {type_filter}

  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "fr,en" .
    ?uri rdfs:label ?label .
    OPTIONAL {{ ?uri schema:description ?comment . }}
  }}
}}
        """.strip()

    data = await sparql.query(query=query, endpoint=endpoint, limit=limit, use_cache=True)
    rows = sparql_json_to_rows(data)

    results: List[SearchResultItem] = []
    for r in rows:
        uri = r.get("uri") or ""
        label = r.get("label") or ""
        comment = r.get("comment")
        if not uri or not label:
            continue
        results.append(
            SearchResultItem(
                uri=uri,
                label=label,
                description=comment,
                type=entity_type,
            )
        )

    return SearchResponse(
        meta=ApiMeta(endpoint=endpoint, limit=limit, cached=False),
        query=q,
        entity_type=entity_type,
        results=results,
    )
