from __future__ import annotations

from typing import Any, Dict, List, Optional
import time
import logging

from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper.SPARQLExceptions import EndPointInternalError, SPARQLWrapperException


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _normalize_lang(lang: str) -> str:
    lang = (lang or "fr").strip().lower()
    return lang if lang in ("fr", "en") else "fr"


class DBpediaService:
    def __init__(self, endpoint: str = "https://dbpedia.org/sparql", timeout_s: int = 60):
        self.endpoint = endpoint
        self.sparql = SPARQLWrapper(endpoint)

        # IMPORTANT: DBpedia needs explicit JSON accept + format
        self.sparql.setReturnFormat(JSON)
        self.sparql.setTimeout(timeout_s)

        # Force GET (DBpedia can be picky with POST sometimes)
        try:
            self.sparql.setMethod("GET")
        except Exception:
            pass

        # user agent
        try:
            self.sparql.addCustomHttpHeader("User-Agent", "StudentProject-FootballApp/1.0")
        except Exception:
            pass

    def _extract_bindings(self, results: Any) -> List[Dict[str, Any]]:
        if not isinstance(results, dict):
            return []
        res = results.get("results")
        if isinstance(res, dict):
            bindings = res.get("bindings")
            if isinstance(bindings, list):
                return bindings
        return []

    def _run(self, query: str, retries: int = 3) -> List[Dict[str, Any]]:
        """
        Run SPARQL query and return results.bindings as list.

        Robust:
        - retries + backoff
        - logs errors (doesn't silently swallow)
        - ensures JSON output
        """
        attempt = 0
        last_err: Optional[str] = None

        while attempt < retries:
            try:
                self.sparql.setQuery(query)

                # Force JSON at endpoint level too
                # (SPARQLWrapper uses "format" param; DBpedia understands it)
                try:
                    self.sparql.addParameter("format", "application/sparql-results+json")
                except Exception:
                    pass

                results = self.sparql.query().convert()
                bindings = self._extract_bindings(results)

                logger.info("DBpedia _run OK: %d bindings", len(bindings))
                return bindings

            except EndPointInternalError as e:
                # DBpedia returns 500 with message sometimes
                last_err = f"EndPointInternalError: {e}"
                attempt += 1
                logger.warning("DBpedia attempt %d/%d failed: %s", attempt, retries, last_err)
                time.sleep(0.6 * attempt)

            except SPARQLWrapperException as e:
                last_err = f"SPARQLWrapperException: {e}"
                attempt += 1
                logger.warning("DBpedia attempt %d/%d failed: %s", attempt, retries, last_err)
                time.sleep(0.6 * attempt)

            except Exception as e:
                # Keep the error visible (this was your issue: it silently returns [])
                last_err = f"Unexpected error: {type(e).__name__}: {e}"
                attempt += 1
                logger.warning("DBpedia attempt %d/%d failed: %s", attempt, retries, last_err)
                time.sleep(0.6 * attempt)

        logger.error("DBpedia _run FAILED after %d retries. Last error: %s", retries, last_err)
        return []

    # ---------------------------
    # Curated endpoints used by front
    # ---------------------------

    def get_specific_players(self, lang: str = "fr") -> List[Dict[str, Any]]:
        lang = _normalize_lang(lang)

        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dbp: <http://dbpedia.org/property/>

SELECT ?uri
       (SAMPLE(?finalName) as ?nom)
       (SAMPLE(?clubLabel2) as ?club)
       (SAMPLE(?img2) as ?image)
WHERE {{
  VALUES ?uri {{
    dbr:Lionel_Messi
    dbr:Cristiano_Ronaldo
    dbr:Neymar
    dbr:Lamine_Yamal
    dbr:Zinedine_Zidane
  }}

  OPTIONAL {{ ?uri rdfs:label ?labelFR . FILTER(lang(?labelFR) = 'fr') }}
  OPTIONAL {{ ?uri rdfs:label ?labelEN . FILTER(lang(?labelEN) = 'en') }}
  BIND(COALESCE(?labelFR, ?labelEN, STR(?uri)) AS ?finalName)

  OPTIONAL {{
    ?uri (dbo:currentTeam|dbo:team|dbp:currentclub) ?team .
    ?team rdfs:label ?clubLabel .
    FILTER(lang(?clubLabel) = '{lang}' || lang(?clubLabel) = 'en' || lang(?clubLabel) = 'fr')
  }}
  BIND(COALESCE(?clubLabel, "Légende / Retraité") AS ?clubLabel2)

  OPTIONAL {{ ?uri dbo:thumbnail ?img }}
  BIND(COALESCE(?img, "https://via.placeholder.com/150") AS ?img2)
}}
GROUP BY ?uri
""".strip()

        bindings = self._run(query)

        joueurs = []
        for item in bindings:
            joueurs.append({
                "nom": item.get("nom", {}).get("value"),
                "club": item.get("club", {}).get("value", "Légende / Retraité"),
                "image": item.get("image", {}).get("value", "https://via.placeholder.com/150"),
            })
        return joueurs

    def get_specific_clubs(self, lang: str = "fr") -> List[Dict[str, Any]]:
        lang = _normalize_lang(lang)

        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?uri ?nom
       (SAMPLE(?stadeLabel2) as ?stade)
       (SAMPLE(?capacite2) as ?cap)
       (SAMPLE(?img2) as ?image)
WHERE {{
  VALUES ?uri {{
    <http://dbpedia.org/resource/FC_Barcelona>
    <http://dbpedia.org/resource/Real_Madrid_CF>
    <http://dbpedia.org/resource/Paris_Saint-Germain_F.C.>
    <http://dbpedia.org/resource/Manchester_City_F.C.>
    <http://dbpedia.org/resource/FC_Bayern_Munich>
  }}

  ?uri rdfs:label ?nom .
  FILTER(lang(?nom) = '{lang}' || lang(?nom) = 'en' || lang(?nom) = 'fr')

  OPTIONAL {{
    ?uri dbo:ground ?ground .
    ?ground rdfs:label ?stadeLabel .
    FILTER(lang(?stadeLabel) = '{lang}' || lang(?stadeLabel) = 'en' || lang(?stadeLabel) = 'fr' || lang(?stadeLabel) = '')
    OPTIONAL {{ ?ground dbo:capacity ?capacite }}
  }}

  BIND(COALESCE(?stadeLabel, "Stade inconnu") AS ?stadeLabel2)
  BIND(COALESCE(?capacite, "N/A") AS ?capacite2)

  OPTIONAL {{ ?uri dbo:thumbnail ?img }}
  BIND(COALESCE(?img, "https://via.placeholder.com/150") AS ?img2)
}}
GROUP BY ?uri ?nom
""".strip()

        bindings = self._run(query)

        clubs = []
        for item in bindings:
            clubs.append({
                "nom": item.get("nom", {}).get("value"),
                "stade": item.get("stade", {}).get("value", "Stade inconnu"),
                "capacite": item.get("cap", {}).get("value", "N/A"),
                "image": item.get("image", {}).get("value", "https://via.placeholder.com/150"),
            })
        return clubs

    def get_top_competitions(self, lang: str = "fr") -> List[Dict[str, Any]]:
        lang = _normalize_lang(lang)

        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?uri ?nom
       (SAMPLE(?pays2) as ?pays)
       (SAMPLE(?img2) as ?image)
WHERE {{
  VALUES ?uri {{
    <http://dbpedia.org/resource/UEFA_Champions_League>
    <http://dbpedia.org/resource/Premier_League>
    <http://dbpedia.org/resource/La_Liga>
    <http://dbpedia.org/resource/Ligue_1>
    <http://dbpedia.org/resource/Bundesliga>
    <http://dbpedia.org/resource/Serie_A>
  }}

  ?uri rdfs:label ?nom .
  FILTER(lang(?nom) = '{lang}' || lang(?nom) = 'en' || lang(?nom) = 'fr')

  OPTIONAL {{
    ?uri dbo:country ?country .
    ?country rdfs:label ?paysLabel .
    FILTER(lang(?paysLabel) = '{lang}' || lang(?paysLabel) = 'en' || lang(?paysLabel) = 'fr')
  }}
  BIND(COALESCE(?paysLabel, "Europe") AS ?pays2)

  OPTIONAL {{ ?uri dbo:thumbnail ?img }}
  BIND(COALESCE(?img, "https://via.placeholder.com/150") AS ?img2)
}}
GROUP BY ?uri ?nom
""".strip()

        bindings = self._run(query)

        comps = []
        for item in bindings:
            comps.append({
                "nom": item.get("nom", {}).get("value"),
                "pays": item.get("pays", {}).get("value", "Europe"),
                "image": item.get("image", {}).get("value", "https://via.placeholder.com/150"),
            })
        return comps

    # Analytics: inchangés mais utilisent _run (déjà ok chez toi)
    def analytics_club_degree(self, lang: str = "fr", limit: int = 10) -> List[Dict[str, Any]]:
        lang = _normalize_lang(lang)
        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?club ?clubLabel (COUNT(DISTINCT ?player) AS ?nbPlayers) (SAMPLE(?img) AS ?image) WHERE {{
  ?player a dbo:SoccerPlayer ;
          dbo:team ?club .

  OPTIONAL {{
    ?club rdfs:label ?clubLabel .
    FILTER(lang(?clubLabel) = '{lang}' || lang(?clubLabel) = 'en' || lang(?clubLabel) = 'fr')
  }}
  OPTIONAL {{ ?club dbo:thumbnail ?img }}
}}
GROUP BY ?club ?clubLabel
ORDER BY DESC(?nbPlayers)
LIMIT {int(limit)}
""".strip()

        bindings = self._run(query)
        out = []
        for b in bindings:
            out.append({
                "club_uri": b.get("club", {}).get("value"),
                "club": b.get("clubLabel", {}).get("value") or b.get("club", {}).get("value"),
                "nbPlayers": int(float(b.get("nbPlayers", {}).get("value", "0"))),
                "image": b.get("image", {}).get("value", None),
            })
        return out

    def analytics_player_mobility(self, lang: str = "fr", limit: int = 10, min_clubs: int = 2) -> List[Dict[str, Any]]:
        lang = _normalize_lang(lang)
        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?player ?playerLabel (COUNT(DISTINCT ?club) AS ?nbClubs) (SAMPLE(?img) AS ?image) WHERE {{
  ?player a dbo:SoccerPlayer ;
          dbo:team ?club .

  OPTIONAL {{
    ?player rdfs:label ?playerLabel .
    FILTER(lang(?playerLabel) = '{lang}' || lang(?playerLabel) = 'en' || lang(?playerLabel) = 'fr')
  }}
  OPTIONAL {{ ?player dbo:thumbnail ?img }}
}}
GROUP BY ?player ?playerLabel
HAVING (COUNT(DISTINCT ?club) >= {int(min_clubs)})
ORDER BY DESC(?nbClubs)
LIMIT {int(limit)}
""".strip()

        bindings = self._run(query)
        out = []
        for b in bindings:
            out.append({
                "player_uri": b.get("player", {}).get("value"),
                "player": b.get("playerLabel", {}).get("value") or b.get("player", {}).get("value"),
                "nbClubs": int(float(b.get("nbClubs", {}).get("value", "0"))),
                "image": b.get("image", {}).get("value", None),
            })
        return out

    def analytics_players_clubs_edges(self, lang: str = "fr", limit_edges: int = 500) -> Dict[str, Any]:
        lang = _normalize_lang(lang)

        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?player ?playerLabel ?club ?clubLabel WHERE {{
  ?player a dbo:SoccerPlayer ;
          dbo:team ?club .

  OPTIONAL {{ ?player rdfs:label ?playerLabel . FILTER(lang(?playerLabel) = '{lang}' || lang(?playerLabel) = 'en' || lang(?playerLabel) = 'fr') }}
  OPTIONAL {{ ?club rdfs:label ?clubLabel . FILTER(lang(?clubLabel) = '{lang}' || lang(?clubLabel) = 'en' || lang(?clubLabel) = 'fr') }}
}}
LIMIT {int(limit_edges)}
""".strip()

        rows = self._run(query)

        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []

        def add_node(uri: str, label: str, ntype: str):
            if not uri:
                return
            if uri not in nodes:
                nodes[uri] = {"id": uri, "label": label or uri, "type": ntype}

        for b in rows:
            p_uri = b.get("player", {}).get("value")
            c_uri = b.get("club", {}).get("value")
            p_label = b.get("playerLabel", {}).get("value") or p_uri
            c_label = b.get("clubLabel", {}).get("value") or c_uri
            if not p_uri or not c_uri:
                continue

            add_node(p_uri, p_label, "player")
            add_node(c_uri, c_label, "club")
            edges.append({"source": p_uri, "target": c_uri, "label": "team"})

        return {"nodes": list(nodes.values()), "edges": edges}


dbpedia_service = DBpediaService()
