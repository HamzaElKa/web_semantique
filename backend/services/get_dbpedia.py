from __future__ import annotations

from typing import Any, Dict, List, Optional
from SPARQLWrapper import SPARQLWrapper, JSON


class DBpediaService:
    def __init__(self, endpoint: str = "https://dbpedia.org/sparql"):
        self.sparql = SPARQLWrapper(endpoint)
        self.sparql.setReturnFormat(JSON)

    def _run(self, query: str) -> List[Dict[str, Any]]:
        try:
            self.sparql.setQuery(query)
            results = self.sparql.query().convert()
            return results.get("results", {}).get("bindings", []) or []
        except Exception:
            return []

    @staticmethod
    def _val(b: Dict[str, Any], key: str) -> Optional[str]:
        return b.get(key, {}).get("value")

    # ---------- FOOT SEARCH (clean) ----------

    def search_players(self, q: str, lang: str = "en", limit: int = 20) -> List[Dict[str, Optional[str]]]:
        q = q.strip().replace('"', '\\"')
        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?uri ?label ?comment WHERE {{
  ?uri a dbo:SoccerPlayer ;
       rdfs:label ?label .
  FILTER(lang(?label) = "{lang}")
  FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{q}")))

  OPTIONAL {{
    ?uri rdfs:comment ?comment .
    FILTER(lang(?comment) = "{lang}")
  }}
}}
LIMIT {int(limit)}
""".strip()

        out = []
        for b in self._run(query):
            out.append({
                "uri": self._val(b, "uri"),
                "label": self._val(b, "label"),
                "comment": self._val(b, "comment"),
            })
        return [x for x in out if x["uri"] and x["label"]]

    def search_clubs(self, q: str, lang: str = "en", limit: int = 20) -> List[Dict[str, Optional[str]]]:
        q = q.strip().replace('"', '\\"')
        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?uri ?label ?comment WHERE {{
  ?uri a dbo:SoccerClub ;
       rdfs:label ?label .
  FILTER(lang(?label) = "{lang}")
  FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{q}")))

  OPTIONAL {{
    ?uri rdfs:comment ?comment .
    FILTER(lang(?comment) = "{lang}")
  }}
}}
LIMIT {int(limit)}
""".strip()

        out = []
        for b in self._run(query):
            out.append({
                "uri": self._val(b, "uri"),
                "label": self._val(b, "label"),
                "comment": self._val(b, "comment"),
            })
        return [x for x in out if x["uri"] and x["label"]]

    def search_stadiums(self, q: str, lang: str = "en", limit: int = 20) -> List[Dict[str, Optional[str]]]:
        q = q.strip().replace('"', '\\"')
        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?uri ?label ?comment WHERE {{
  ?uri a dbo:Stadium ;
       rdfs:label ?label .
  FILTER(lang(?label) = "{lang}")
  FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{q}")))

  OPTIONAL {{
    ?uri rdfs:comment ?comment .
    FILTER(lang(?comment) = "{lang}")
  }}
}}
LIMIT {int(limit)}
""".strip()

        out = []
        for b in self._run(query):
            out.append({
                "uri": self._val(b, "uri"),
                "label": self._val(b, "label"),
                "comment": self._val(b, "comment"),
            })
        return [x for x in out if x["uri"] and x["label"]]

    # ---------- ENTITY (player/club) ----------
    def player_profile(self, uri: str, lang: str = "en") -> Dict[str, Any]:
        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

SELECT ?label ?abstract ?birthDate ?height ?positionLabel ?clubLabel ?countryLabel WHERE {{
  BIND(<{uri}> AS ?p)

  OPTIONAL {{ ?p rdfs:label ?label . FILTER(lang(?label)="{lang}") }}
  OPTIONAL {{ ?p dbo:abstract ?abstract . FILTER(lang(?abstract)="{lang}") }}
  OPTIONAL {{ ?p dbo:birthDate ?birthDate . }}
  OPTIONAL {{ ?p dbo:height ?height . }}

  OPTIONAL {{
    ?p dbo:position ?position .
    ?position rdfs:label ?positionLabel .
    FILTER(lang(?positionLabel)="{lang}")
  }}

  OPTIONAL {{
    ?p dbo:team ?club .
    ?club rdfs:label ?clubLabel .
    FILTER(lang(?clubLabel)="{lang}")
  }}

  OPTIONAL {{
    ?p dbo:nationality ?country .
    ?country rdfs:label ?countryLabel .
    FILTER(lang(?countryLabel)="{lang}")
  }}
}}
LIMIT 50
""".strip()

        rows = self._run(query)
        # retourne brut + un petit résumé simple
        return {
            "uri": uri,
            "rows": rows,
        }

    def club_profile(self, uri: str, lang: str = "en") -> Dict[str, Any]:
        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?label ?abstract ?groundLabel ?coachLabel ?leagueLabel WHERE {{
  BIND(<{uri}> AS ?c)

  OPTIONAL {{ ?c rdfs:label ?label . FILTER(lang(?label)="{lang}") }}
  OPTIONAL {{ ?c dbo:abstract ?abstract . FILTER(lang(?abstract)="{lang}") }}

  OPTIONAL {{
    ?c dbo:ground ?g .
    ?g rdfs:label ?groundLabel .
    FILTER(lang(?groundLabel)="{lang}")
  }}

  OPTIONAL {{
    ?c dbo:manager ?coach .
    ?coach rdfs:label ?coachLabel .
    FILTER(lang(?coachLabel)="{lang}")
  }}

  OPTIONAL {{
    ?c dbo:league ?league .
    ?league rdfs:label ?leagueLabel .
    FILTER(lang(?leagueLabel)="{lang}")
  }}
}}
LIMIT 50
""".strip()

        rows = self._run(query)
        return {
            "uri": uri,
            "rows": rows,
        }

    # ---------- existing ones ----------
    def get_stadiums_in_city(self, city: str, lang: str = "fr", limit: int = 50) -> List[Dict[str, str]]:
        city_resource = city.strip().replace(" ", "_")
        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?nomStade ?capacite
WHERE {{
    ?stade a dbo:Stadium ;
           dbo:location dbr:{city_resource} ;
           dbo:capacity ?capacite .
    ?stade rdfs:label ?nomStade .
    FILTER (lang(?nomStade) = '{lang}')
}}
ORDER BY DESC(?capacite)
LIMIT {int(limit)}
""".strip()

        bindings = self._run(query)
        out: List[Dict[str, str]] = []
        for b in bindings:
            nom = self._val(b, "nomStade")
            cap = self._val(b, "capacite")
            if nom:
                out.append({"nom": nom, "capacite": cap})
        return out

    def get_psg_info(self, lang: str = "fr") -> Optional[Dict[str, Optional[str]]]:
        query = f"""
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?nom ?stadeLabel ?coachLabel WHERE {{
  BIND(<http://dbpedia.org/resource/Paris_Saint-Germain_F.C.> AS ?club)

  ?club rdfs:label ?nom .
  FILTER (lang(?nom) = '{lang}')

  OPTIONAL {{
    ?club dbo:ground ?stade .
    ?stade rdfs:label ?stadeLabel .
    FILTER (lang(?stadeLabel) = '{lang}')
  }}

  OPTIONAL {{ ?club dbo:manager ?coach . }}
  OPTIONAL {{ ?club dbo:coach ?coach . }}
  OPTIONAL {{ ?club dbo:trainer ?coach . }}

  OPTIONAL {{
    ?coach rdfs:label ?coachLabel .
    FILTER (lang(?coachLabel) = '{lang}')
  }}
}}
LIMIT 1
""".strip()

        bindings = self._run(query)
        if not bindings:
            return None
        b = bindings[0]
        return {
            "club": self._val(b, "nom"),
            "stade": self._val(b, "stadeLabel"),
            "coach": self._val(b, "coachLabel"),
        }


dbpedia_service = DBpediaService()
