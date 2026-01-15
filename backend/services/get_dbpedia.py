from __future__ import annotations

from typing import Any, Dict, List, Optional
import re
import logging

from SPARQLWrapper import SPARQLWrapper, JSON

logger = logging.getLogger(__name__)


def _to_dbpedia_resource(label: str) -> str:
    """
    Very small heuristic to turn a city label into a DBpedia resource QName.
    Example: "San Francisco" -> "San_Francisco"
    """
    s = (label or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace(" ", "_")
    # Remove characters that often break QNames
    s = re.sub(r"[^A-Za-z0-9_()\-]", "", s)
    return s


def _normalize_lang(lang: str) -> str:
    lang = (lang or "fr").strip().lower()
    return lang if lang in ("fr", "en") else "fr"


class DBpediaService:
    def __init__(self, endpoint: str = "https://dbpedia.org/sparql", timeout_s: int = 20):
        self.endpoint = endpoint
        self.sparql = SPARQLWrapper(endpoint)
        self.sparql.setReturnFormat(JSON)
        self.sparql.setTimeout(timeout_s)

        # Helpful for endpoints (polite / avoids blocks in some cases)
        # SPARQLWrapper supports addCustomHttpHeader
        try:
            self.sparql.addCustomHttpHeader(
                "User-Agent",
                "4IF-WS-Foot-Explorer/1.0 (INSA Lyon; contact: student)",
            )
        except Exception:
            # Not critical
            pass

    def _run(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a SPARQL query and return bindings.
        Returns [] if DBpedia is down / under maintenance / query error,
        so the API stays stable.
        """
        try:
            self.sparql.setQuery(query)
            results = self.sparql.query().convert()

            bindings = results.get("results", {}).get("bindings", [])
            if isinstance(bindings, list):
                return bindings
            return []
        except Exception as e:
            # Keep API stable, but log for debugging
            logger.warning("DBpedia query failed: %s", e)
            return []

    def get_stadiums_in_city(self, city: str, lang: str = "fr", limit: int = 50) -> List[Dict[str, Optional[str]]]:
        lang = _normalize_lang(lang)
        limit = max(1, min(int(limit), 200))

        city_resource = _to_dbpedia_resource(city)
        if not city_resource:
            return []

        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?nomStade ?capacite WHERE {{
  ?stade a dbo:Stadium ;
         dbo:location dbr:{city_resource} .
  OPTIONAL {{ ?stade dbo:capacity ?capacite . }}
  ?stade rdfs:label ?nomStade .
  FILTER(lang(?nomStade) = '{lang}')
}}
ORDER BY DESC(xsd:integer(?capacite))
LIMIT {limit}
""".strip()

        bindings = self._run(query)

        stades: List[Dict[str, Optional[str]]] = []
        for item in bindings:
            nom = item.get("nomStade", {}).get("value")
            cap = item.get("capacite", {}).get("value") if item.get("capacite") else None
            if not nom:
                continue
            stades.append({"nom": nom, "capacite": cap})

        return stades

    def get_psg_info(self, lang: str = "fr") -> Optional[Dict[str, Optional[str]]]:
        lang = _normalize_lang(lang)

        # PSG URI contains dots, so we must use full IRI <...>
        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?nom ?stadeLabel ?coachLabel WHERE {{
  BIND(<http://dbpedia.org/resource/Paris_Saint-Germain_F.C.> AS ?club)

  ?club rdfs:label ?nom .
  FILTER(lang(?nom) = '{lang}')

  OPTIONAL {{
    ?club dbo:ground ?stade .
    ?stade rdfs:label ?stadeLabel .
    FILTER(lang(?stadeLabel) = '{lang}')
  }}

  OPTIONAL {{ ?club dbo:manager ?coach . }}
  OPTIONAL {{ ?club dbo:coach ?coach . }}
  OPTIONAL {{ ?club dbo:trainer ?coach . }}

  OPTIONAL {{
    ?coach rdfs:label ?coachLabel .
    FILTER(lang(?coachLabel) = '{lang}')
  }}
}}
LIMIT 1
""".strip()

        bindings = self._run(query)
        if not bindings:
            return None

        b = bindings[0]
        return {
            "club": b.get("nom", {}).get("value"),
            "stade": b.get("stadeLabel", {}).get("value"),
            "coach": b.get("coachLabel", {}).get("value"),
        }


dbpedia_service = DBpediaService()
