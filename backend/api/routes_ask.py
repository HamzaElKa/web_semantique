from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import AskRequest, AskResponse, ApiMeta, EndpointName
from api.config import settings
from api.deps import get_sparql_client
from services.sparql_client import SparqlClient
from services.normalize import sparql_json_to_rows

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    sparql: SparqlClient = Depends(get_sparql_client),
):
    # Pick endpoint
    endpoint: EndpointName = (payload.endpoint or settings.DEFAULT_ENDPOINT).lower()  # type: ignore

    # This route is currently a placeholder "NL -> SPARQL".
    # IMPORTANT: the sample queries below are DBpedia-oriented (dbo:...).
    if endpoint == "wikidata":
        raise HTTPException(
            status_code=400,
            detail="Ce endpoint (wikidata) n'est pas encore supporté par /ask (stub). Utilise endpoint=dbpedia.",
        )

    q = (payload.question or "").strip().lower()
    if not q:
        raise HTTPException(status_code=400, detail="question is required")

    # Very small heuristic "NL2SPARQL" stub (to be replaced by LLM)
    if ("club" in q or "clubs" in q) and ("brésilien" in q or "bresilien" in q or "brazil" in q):
        generated = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dbo:  <http://dbpedia.org/ontology/>

SELECT ?club ?label (COUNT(?player) AS ?n) WHERE {
  ?player dbo:team ?club .
  ?player dbo:nationality ?nat .
  ?nat rdfs:label ?natLabel .
  FILTER(lang(?natLabel)="en" && CONTAINS(LCASE(STR(?natLabel)), "brazil"))

  ?club rdfs:label ?label .
  FILTER(lang(?label) IN ("en","fr"))
}
GROUP BY ?club ?label
ORDER BY DESC(?n)
        """.strip()
    else:
        generated = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?uri ?label WHERE {
  ?uri rdfs:label ?label .
  FILTER(lang(?label) IN ("en","fr"))
  FILTER(CONTAINS(LCASE(STR(?label)), "football"))
}
LIMIT 50
        """.strip()

    # Limit guards
    limit = min(settings.DEFAULT_LIMIT, settings.MAX_LIMIT)
    if limit <= 0:
        limit = 50

    data = await sparql.query(
        query=generated,
        endpoint="dbpedia",
        limit=limit,
        use_cache=True,
    )
    rows = sparql_json_to_rows(data)

    answer = (
        f"J'ai trouvé {len(rows)} résultats (extrait). "
        "Branche le module LLM pour une synthèse plus intelligente."
    )

    return AskResponse(
        meta=ApiMeta(endpoint="dbpedia", limit=limit, cached=False),
        question=payload.question,
        generated_sparql=generated,
        rows=rows[:50],
        answer=answer,
    )
