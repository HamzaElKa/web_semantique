from __future__ import annotations

from fastapi import APIRouter, Query
from services.get_dbpedia import dbpedia_service

router = APIRouter(prefix="/dbpedia-foot", tags=["dbpedia-foot"])


@router.get("/search/players")
def search_players(
    q: str = Query(..., min_length=2),
    lang: str = Query("en"),
    limit: int = Query(20, ge=1, le=50),
):
    results = dbpedia_service.search_players(q=q, lang=lang, limit=limit)
    return {"q": q, "type": "player", "lang": lang, "count": len(results), "results": results}


@router.get("/search/clubs")
def search_clubs(
    q: str = Query(..., min_length=2),
    lang: str = Query("en"),
    limit: int = Query(20, ge=1, le=50),
):
    results = dbpedia_service.search_clubs(q=q, lang=lang, limit=limit)
    return {"q": q, "type": "club", "lang": lang, "count": len(results), "results": results}


@router.get("/search/stadiums")
def search_stadiums(
    q: str = Query(..., min_length=2),
    lang: str = Query("en"),
    limit: int = Query(20, ge=1, le=50),
):
    results = dbpedia_service.search_stadiums(q=q, lang=lang, limit=limit)
    return {"q": q, "type": "stadium", "lang": lang, "count": len(results), "results": results}


@router.get("/player")
def player_profile(
    uri: str = Query(..., description="DBpedia URI of the player"),
    lang: str = Query("en"),
):
    return dbpedia_service.player_profile(uri=uri, lang=lang)


@router.get("/club")
def club_profile(
    uri: str = Query(..., description="DBpedia URI of the club"),
    lang: str = Query("en"),
):
    return dbpedia_service.club_profile(uri=uri, lang=lang)
