from __future__ import annotations
from fastapi import APIRouter, Query
from api.schemas import SimilarityResponse, ApiMeta, EndpointName
from api.config import settings

router = APIRouter(prefix="/similarity", tags=["similarity"])

@router.get("", response_model=SimilarityResponse)
async def similarity(
    entity_type: str = Query("player"),
    id: str = Query(...),
    endpoint: EndpointName = Query(settings.DEFAULT_ENDPOINT),
    limit: int = Query(20, ge=1, le=100),
):
    # Ce module sera alimenté par ton collègue "analysis_similarity".
    # Pour l’instant, on renvoie un format stable pour que le front puisse avancer.
    return SimilarityResponse(
        meta=ApiMeta(endpoint=endpoint, limit=limit, cached=False),
        entity_type=entity_type,
        uri=id,
        similar=[],
    )
