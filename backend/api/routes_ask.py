from fastapi import APIRouter, Depends, HTTPException
from api.schemas import AskRequest, AskResponse, ApiMeta
from api.deps import get_sparql_client 
from services.sparql_client import SparqlClient
from services.normalize import sparql_json_to_rows
from services.llm_service import analyze_football_intent
# On importe les fonctions depuis le service que tu as fusionné
from services.ask_service import build_sparql_player_club, build_sparql_club_stadium, format_answer

router = APIRouter(prefix="/ask", tags=["ask"])

@router.post("", response_model=AskResponse)
async def ask(
    payload: AskRequest, 
    sparql: SparqlClient = Depends(get_sparql_client)
):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    # 1. IA analyse l'intention via Ollama (Mistral/Llama)
    # Cette étape valide la consigne 3.3 : NL2Entity
    analysis = analyze_football_intent(question)
    intent = analysis.get("intent", "player_club")
    entity = analysis.get("entity", question)

    # 2. Choix de la requête SPARQL (NL2SPARQL)
    limit = 10
    if intent == "club_stadium":
        query = build_sparql_club_stadium(entity, limit=limit)
    else:
        query = build_sparql_player_club(entity, limit=limit)

    # 3. Exécution de la requête avec l'argument 'limit' (Correctif erreur 500)
    try:
        data = await sparql.query(
            query=query, 
            endpoint="dbpedia", 
            limit=limit,      # Ajout de l'argument obligatoire
            use_cache=True
        )
        rows = sparql_json_to_rows(data)
    except Exception as e:
        raise HTTPException(
            status_code=504, 
            detail=f"Erreur lors de la requête DBpedia : {e}"
        )

    # 4. Synthèse de connaissances (Réponse pédagogique)
    # On transforme les données brutes en phrase naturelle
    answer = format_answer(intent, entity, rows)

    # 5. Retour conforme au schéma AskResponse pour ask.js
    return AskResponse(
        meta=ApiMeta(endpoint="dbpedia", limit=limit, cached=False),
        question=question,
        generated_sparql=query,
        rows=rows,
        answer=answer
    )