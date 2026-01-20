from __future__ import annotations

from fastapi import APIRouter, Query
from services.get_dbpedia import dbpedia_service as dbpedia


router = APIRouter(prefix="/dbpedia-foot", tags=["dbpedia-foot"])

def _normalize_lang(lang: str) -> str:
    lang = (lang or "fr").strip().lower()
    return lang if lang in ("fr", "en") else "fr"


@router.get("/status")
def status():
    """
    Petit ping DBpedia: utile pour debug.
    """
    # mini requête safe
    q = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT (COUNT(*) AS ?n) WHERE { ?s rdfs:label ?o } LIMIT 1
""".strip()
    rows = dbpedia._run(q, retries=1)
    return {"ok": True, "bindings_len": len(rows)}


# ---------------------------
# HOME DATA (ce que ton front veut)
# ---------------------------

@router.get("/players")
def specific_players(lang: str = Query("fr")):
    """
    Renvoie une liste "curated" de joueurs (Messi, CR7, Neymar, Yamal, Zidane)
    avec nom/club/image, nettoyée par ton service.
    """
    lang = _normalize_lang(lang)
    data = dbpedia.get_specific_players(lang=lang)
    return {"lang": lang, "count": len(data), "results": data}


@router.get("/clubs")
def specific_clubs(lang: str = Query("fr")):
    """
    Renvoie une liste "curated" de clubs (Barça, Real, PSG, Man City, Bayern)
    avec nom/stade/capacite/image, nettoyée par ton service.
    """
    lang = _normalize_lang(lang)
    data = dbpedia.get_specific_clubs(lang=lang)
    return {"lang": lang, "count": len(data), "results": data}


@router.get("/competitions")
def top_competitions(lang: str = Query("fr")):
    """
    Renvoie une liste "curated" de compétitions (UCL, PL, Liga, L1, Bundesliga, Serie A)
    avec nom/pays/image, nettoyée par ton service.
    """
    lang = _normalize_lang(lang)
    data = dbpedia.get_top_competitions(lang=lang)
    return {"lang": lang, "count": len(data), "results": data}

@router.get("/analytics/club-degree")
def club_degree(lang: str = Query("fr"), limit: int = Query(10, ge=1, le=50)):
    lang = _normalize_lang(lang)
    data = dbpedia.analytics_club_degree(lang=lang, limit=limit)
    return {"lang": lang, "count": len(data), "results": data}


@router.get("/analytics/player-mobility")
def player_mobility(
    lang: str = Query("fr"),
    limit: int = Query(10, ge=1, le=50),
    min_clubs: int = Query(2, ge=2, le=10),
):
    lang = _normalize_lang(lang)
    data = dbpedia.analytics_player_mobility(lang=lang, limit=limit, min_clubs=min_clubs)
    return {"lang": lang, "count": len(data), "results": data}


@router.get("/analytics/players-clubs-graph")
def players_clubs_graph(lang: str = Query("fr"), limit_edges: int = Query(500, ge=50, le=2000)):
    lang = _normalize_lang(lang)
    g = dbpedia.analytics_players_clubs_edges(lang=lang, limit_edges=limit_edges)
    return {"lang": lang, **g}

# ---------------------------
# (Optionnel) endpoint agrégé pour page d'accueil
# ---------------------------

@router.get("/home")
def home(lang: str = Query("fr")):
    """
    Tout en 1 appel: clubs + players + competitions
    -> pratique pour un front simple en HTML/JS.
    """
    lang = _normalize_lang(lang)
    return {
        "lang": lang,
        "clubs": dbpedia.get_specific_clubs(lang=lang),
        "players": dbpedia.get_specific_players(lang=lang),
        "competitions": dbpedia.get_top_competitions(lang=lang),
    }
