from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Query

from services.get_dbpedia import dbpedia_service

router = APIRouter(prefix="/dbpedia", tags=["dbpedia"])


@router.get("/stadiums")
def stadiums_in_city(
    city: str = Query(..., min_length=2, description="City name mapped to DBpedia resource (spaces replaced by underscores)"),
    lang: str = Query("fr", pattern="^(fr|en)$", description="Label language (fr or en)"),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    stades = dbpedia_service.get_stadiums_in_city(city=city, lang=lang, limit=limit)

    note: Optional[str] = None
    if len(stades) == 0:
        note = "No results (DBpedia may be under maintenance or city resource not found)."

    return {
        "city": city,
        "lang": lang,
        "count": len(stades),
        "results": stades,
        "note": note,
    }


@router.get("/psg")
def psg_info(
    lang: str = Query("fr", pattern="^(fr|en)$", description="Label language (fr or en)"),
) -> Dict[str, Any]:
    info = dbpedia_service.get_psg_info(lang=lang)
    return {
        "lang": lang,
        "found": info is not None,
        "result": info,
        "note": None if info is not None else "No result (DBpedia may be under maintenance).",
    }
