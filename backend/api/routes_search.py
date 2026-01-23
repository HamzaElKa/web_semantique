from __future__ import annotations

from typing import List, Literal
from fastapi import APIRouter, Depends, Query

from api.schemas import SearchResponse, ApiMeta, SearchResultItem
from api.config import settings
from api.deps import get_sparql_client
from services.sparql_client import SparqlClient
from services.normalize import sparql_json_to_rows

router = APIRouter(prefix="/search", tags=["search"])

EntityType = Literal["player", "club", "stadium"]


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
    limit: int = Query(settings.DEFAULT_LIMIT, ge=1, le=settings.MAX_LIMIT),
    sparql: SparqlClient = Depends(get_sparql_client),
):
    q_escaped = _clean_search_text(q)

    # DBpedia search: label contains q (fr/en) + optional short comment.
    # We keep "hints" depending on entity_type, without strict filtering (better recall for demo).
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

    data = await sparql.query(query=query, endpoint="dbpedia", limit=limit, use_cache=True)
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
        meta=ApiMeta(endpoint="dbpedia", limit=limit, cached=False),
        query=q,
        entity_type=entity_type,
        results=results,
    )
