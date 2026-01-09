from __future__ import annotations
from fastapi import APIRouter, Depends
from api.schemas import AskRequest, AskResponse, ApiMeta, EndpointName
from api.config import settings
from services.sparql_client import SparqlClient
from services.normalize import sparql_json_to_rows

router = APIRouter(prefix="/ask", tags=["ask"])

@router.post("", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    sparql: SparqlClient = Depends(lambda: __import__("api.deps").deps.get_sparql_client()),
):
    endpoint: EndpointName = payload.endpoint or settings.DEFAULT_ENDPOINT

    # Placeholder NL2SPARQL: le module LLM remplacera ça.
    # On montre déjà le pipeline: question -> sparql -> rows -> answer
    q = payload.question.lower()

    if "club" in q and "brésilien" in q:
        generated = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dbo:  <http://dbpedia.org/ontology/>
        SELECT ?club ?label (COUNT(?player) AS ?n) WHERE {
          ?player dbo:team ?club .
          ?player dbo:nationality ?nat .
          ?nat rdfs:label ?natLabel .
          FILTER(lang(?natLabel)="en" && CONTAINS(LCASE(?natLabel), "brazil"))
          ?club rdfs:label ?label .
          FILTER(lang(?label) IN ("en","fr"))
        }
        GROUP BY ?club ?label
        ORDER BY DESC(?n)
        """
    else:
        generated = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?uri ?label WHERE {
          ?uri rdfs:label ?label .
          FILTER(lang(?label) IN ("en","fr"))
          FILTER(CONTAINS(LCASE(STR(?label)), "football"))
        }
        """

    data = await sparql.query(query=generated, endpoint=endpoint, limit=settings.DEFAULT_LIMIT, use_cache=True)
    rows = sparql_json_to_rows(data)

    answer = f"J'ai trouvé {len(rows)} résultats (extrait). Branche le module LLM pour une synthèse plus intelligente."

    return AskResponse(
        meta=ApiMeta(endpoint=endpoint, limit=settings.DEFAULT_LIMIT, cached=False),
        question=payload.question,
        generated_sparql=generated.strip(),
        rows=rows[:50],
        answer=answer,
    )
