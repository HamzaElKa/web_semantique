from __future__ import annotations

from typing import Any, Dict, List, Optional
import time
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
    def __init__(self, endpoint: str = "https://dbpedia.org/sparql", timeout_s: int = 60):
        self.endpoint = endpoint
        self.sparql = SPARQLWrapper(endpoint)
        self.sparql.setReturnFormat(JSON)
        self.sparql.setTimeout(timeout_s)
        try:
            self.sparql.addCustomHttpHeader("User-Agent", "StudentProject-FootballApp/1.0")
        except Exception:
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
        
        SELECT DISTINCT ?uri ?nom ?stadeLabel ?capacite ?img WHERE {{
            VALUES ?uri {{ 
                dbr:FC_Barcelona 
                dbr:Real_Madrid_CF 
                <http://dbpedia.org/resource/Paris_Saint-Germain_F.C.> 
                <http://dbpedia.org/resource/Manchester_City_F.C.>
                dbr:FC_Bayern_Munich 
            }}

            ?uri rdfs:label ?nom .
            FILTER(lang(?nom) = '{lang}')

            OPTIONAL {{ 
                ?uri (dbo:ground | dbp:stadium) ?stade .
                ?stade rdfs:label ?stadeLabel .
                FILTER(lang(?stadeLabel) = '{lang}')
                OPTIONAL {{ ?stade dbo:capacity ?capacite }}
            }}

            OPTIONAL {{ ?uri dbo:thumbnail ?img }}
        }}
        """
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
        
        SELECT ?uri ?nom (SAMPLE(?stadeLabel) as ?stade) (SAMPLE(?capacite) as ?cap) (SAMPLE(?img) as ?image) WHERE {{
            VALUES ?uri {{ 
                <http://dbpedia.org/resource/FC_Barcelona>
                <http://dbpedia.org/resource/Real_Madrid_CF>
                <http://dbpedia.org/resource/Paris_Saint-Germain_F.C.> 
                <http://dbpedia.org/resource/Manchester_City_F.C.>
                <http://dbpedia.org/resource/FC_Bayern_Munich> 
            }}

            ?uri rdfs:label ?nom .
            FILTER(lang(?nom) = '{lang}')

            OPTIONAL {{ 
                ?uri (dbo:ground|dbp:stadium) ?ground .
                ?ground rdfs:label ?stadeLabel .
                # Astuce : On accepte le label s'il est en FR ou s'il n'a pas de langue, ou en EN
                FILTER(lang(?stadeLabel) = '{lang}' || lang(?stadeLabel) = 'en' || lang(?stadeLabel) = '')
                
                OPTIONAL {{ ?ground dbo:capacity ?capacite }}
            }}

            OPTIONAL {{ ?uri dbo:thumbnail ?img }}
        }}
        GROUP BY ?uri ?nom
        """
        bindings = self._run(query)
        
        clubs = []
        for item in bindings:
            clubs.append({
                "nom": item.get("nom", {}).get("value"),
                "stade": item.get("stade", {}).get("value", "Stade inconnu"),
                "capacite": item.get("cap", {}).get("value", "N/A"),
                "image": item.get("image", {}).get("value", "https://via.placeholder.com/150")
            })
        return clubs

    def get_top_competitions(self, lang: str = "fr") -> List[Dict[str, Any]]:
        """
        Nettoyage : GROUP BY pour éviter les doublons (ex: Allemagne de l'Est/Ouest)
        """
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?uri ?nom (SAMPLE(?paysLabel) as ?pays) (SAMPLE(?img) as ?image) WHERE {{
            VALUES ?uri {{ 
                <http://dbpedia.org/resource/UEFA_Champions_League>
                <http://dbpedia.org/resource/Premier_League>
                <http://dbpedia.org/resource/La_Liga>
                <http://dbpedia.org/resource/Ligue_1>
                <http://dbpedia.org/resource/Bundesliga>
                <http://dbpedia.org/resource/Serie_A>
            }}

            ?uri rdfs:label ?nom .
            FILTER(lang(?nom) = '{lang}')
            
            OPTIONAL {{ 
                ?uri dbo:country ?country . 
                ?country rdfs:label ?paysLabel .
                FILTER(lang(?paysLabel) = '{lang}')
            }}
            
            OPTIONAL {{ ?uri dbo:thumbnail ?img }}
        }}
        GROUP BY ?uri ?nom
        """
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
