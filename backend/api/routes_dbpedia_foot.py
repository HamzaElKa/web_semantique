from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal, Tuple

from fastapi import APIRouter, Query
from services.get_dbpedia import dbpedia_service as dbpedia

router = APIRouter(prefix="/dbpedia-foot", tags=["dbpedia-foot"])


def _normalize_lang(lang: str) -> str:
    lang = (lang or "fr").strip().lower()
    return lang if lang in ("fr", "en") else "fr"


def _escape_bif_term(q: str) -> str:
    q = (q or "").strip()
    q = q.replace('"', " ").replace("'", " ")
    q = " ".join(q.split())
    return q


def _binding_value(b: Dict[str, Any], key: str) -> Optional[str]:
    v = b.get(key)
    if isinstance(v, dict):
        return v.get("value")
    return None


def _bif_literal_for_prefix(term: str) -> str:
    # Virtuoso expects: ?label bif:contains "'messi*'"
    expr = f"'{term}*'"
    return f"\"{expr}\""


def _type_for_kind(kind: str) -> str:
    if kind == "player":
        return "http://dbpedia.org/ontology/SoccerPlayer"
    if kind == "club":
        return "http://dbpedia.org/ontology/SoccerClub"
    if kind == "stadium":
        return "http://dbpedia.org/ontology/Stadium"
    if kind == "competition":
        return "http://dbpedia.org/ontology/SoccerLeague"
    return ""


def _search_fulltext(term: str, lang: str, limit_raw: int) -> List[Dict[str, Any]]:
    if lang == "fr":
        label_langs = '("fr","en")'
        comment_langs = '("fr","en")'
        prefer_expr = 'DESC(lang(?label) = "fr")'
    else:
        label_langs = '("en","fr")'
        comment_langs = '("en","fr")'
        prefer_expr = 'DESC(lang(?label) = "en")'

    bif_literal = _bif_literal_for_prefix(term)

    sparql = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dbo:  <http://dbpedia.org/ontology/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX bif:  <bif:>

SELECT DISTINCT ?uri ?label ?comment (SAMPLE(?img0) AS ?img) WHERE {{
  ?uri rdfs:label ?label .
  FILTER(lang(?label) IN {label_langs}) .
  ?label bif:contains {bif_literal} .

  OPTIONAL {{
    ?uri rdfs:comment ?comment .
    FILTER(lang(?comment) IN {comment_langs}) .
  }}

  OPTIONAL {{ ?uri dbo:thumbnail ?img0 . }}
  OPTIONAL {{ ?uri foaf:depiction ?img0 . }}
}}
GROUP BY ?uri ?label ?comment
ORDER BY {prefer_expr} STRLEN(STR(?label))
LIMIT {int(limit_raw)}
""".strip()

    return dbpedia._run(sparql, retries=2)


def _filter_by_type_batch(uris: List[str], rdf_type: str) -> set:
    """
    Filtre les URIs en 1 requête SPARQL via VALUES.
    Retourne l'ensemble des URIs qui matchent rdf:type demandé.
    """
    if not uris or not rdf_type:
        return set()

    # éviter requêtes énormes
    uris = uris[:200]

    values = "\n".join([f"<{u}>" for u in uris if u])
    sparql = f"""
SELECT DISTINCT ?uri WHERE {{
  VALUES ?uri {{
    {values}
  }}
  ?uri a <{rdf_type}> .
}}
""".strip()

    rows = dbpedia._run(sparql, retries=2)
    ok = set()
    for b in rows:
        u = _binding_value(b, "uri")
        if u:
            ok.add(u)
    return ok


@router.get("/status")
def status():
    q = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT (COUNT(*) AS ?n) WHERE { ?s rdfs:label ?o } LIMIT 1
""".strip()
    rows = dbpedia._run(q, retries=1)
    return {"ok": True, "bindings_len": len(rows)}


Kind = Literal["player", "club", "stadium", "competition"]


@router.get("/search")
def search(
    q: str = Query(..., min_length=2),
    kind: Kind = Query("player"),
    lang: str = Query("fr"),
    limit: int = Query(20, ge=1, le=200),
):
    """
    Search propre:
    - 1 requête full-text (bif:contains)
    - 1 requête batch pour filtrer par type (VALUES)
    - renvoie <= limit résultats
    """
    lang = _normalize_lang(lang)
    term = _escape_bif_term(q)

    # On récupère plus large puis on filtre
    limit_raw = min(120, max(40, limit * 4))
    raw_bindings = _search_fulltext(term=term, lang=lang, limit_raw=limit_raw)

    # Parse raw results
    raw_results: List[Dict[str, Any]] = []
    seen = set()
    for b in raw_bindings:
        uri = _binding_value(b, "uri") or ""
        label = _binding_value(b, "label") or ""
        if not uri or not label:
            continue
        if uri in seen:
            continue
        seen.add(uri)
        raw_results.append(
            {
                "uri": uri,
                "label": label,
                "comment": _binding_value(b, "comment"),
                "img": _binding_value(b, "img"),
            }
        )

    # If no raw results, return empty
    if not raw_results:
        return {"lang": lang, "kind": kind, "count": 0, "results": []}

    # Filter by kind (type) with batch query
    rdf_type = _type_for_kind(kind)
    ok_uris = _filter_by_type_batch([r["uri"] for r in raw_results], rdf_type=rdf_type)

    filtered = [r for r in raw_results if r["uri"] in ok_uris]

    # If filtering is too strict (DBpedia incomplete typing), fallback to raw but mark it
    used_fallback = False
    if not filtered:
        used_fallback = True
        filtered = raw_results

    final = [
        {**r, "kind": kind}
        for r in filtered[:limit]
    ]

    return {
        "lang": lang,
        "kind": kind,
        "count": len(final),
        "used_fallback": used_fallback,
        "results": final,
    }


# ---- Home endpoints ----

@router.get("/players")
def specific_players(lang: str = Query("fr")):
    lang = _normalize_lang(lang)
    data = dbpedia.get_specific_players(lang=lang)
    return {"lang": lang, "count": len(data), "results": data}


@router.get("/clubs")
def specific_clubs(lang: str = Query("fr")):
    lang = _normalize_lang(lang)
    data = dbpedia.get_specific_clubs(lang=lang)
    return {"lang": lang, "count": len(data), "results": data}


@router.get("/competitions")
def top_competitions(lang: str = Query("fr")):
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


@router.get("/home")
def home(lang: str = Query("fr")):
    lang = _normalize_lang(lang)
    return {
        "lang": lang,
        "clubs": dbpedia.get_specific_clubs(lang=lang),
        "players": dbpedia.get_specific_players(lang=lang),
        "competitions": dbpedia.get_top_competitions(lang=lang),
    }
