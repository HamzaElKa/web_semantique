from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, Query, HTTPException

from api.schemas import SimilarityResponse, ApiMeta

router = APIRouter(prefix="/similarity", tags=["similarity"])

EntityType = Literal["player", "club", "stadium"]


def _validate_uri(u: str) -> str:
    u = (u or "").strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        raise HTTPException(status_code=400, detail="id must be a valid http(s) URI")
    return u


@router.get("", response_model=SimilarityResponse)
async def similarity(
    entity_type: EntityType = Query("player"),
    id: str = Query(..., description="Entity URI (http(s))"),
    limit: int = Query(20, ge=1, le=100),
):
    _validate_uri(id)

    # Placeholder: similarity module will fill this later.
    return SimilarityResponse(
        meta=ApiMeta(endpoint="dbpedia", limit=limit, cached=False),
        entity_type=entity_type,
        uri=id,
        similar=[],
    )
