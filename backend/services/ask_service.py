from __future__ import annotations
import re
from typing import Any, Dict, List

def _safe_contains(text: str) -> str:
    return (text or "").strip().lower().replace('"', '\\"').replace("\\", "")

# --- GÉNÉRATEUR JOUEUR -> CLUB ---
def build_sparql_player_club(player_name: str, limit: int = 10) -> str:
    safe = _safe_contains(player_name)
    return f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dbo:  <http://dbpedia.org/ontology/>
SELECT DISTINCT ?playerLabel ?clubLabel WHERE {{
  ?p a dbo:SoccerPlayer ; rdfs:label ?playerLabel .
  FILTER(lang(?playerLabel) IN ("fr","en")) .
  FILTER(CONTAINS(LCASE(STR(?playerLabel)), "{safe}")) .
  {{ ?p dbo:team ?club . }} UNION {{ ?p <http://dbpedia.org/property/currentclub> ?club . }}
  ?club rdfs:label ?clubLabel .
  FILTER(lang(?clubLabel) IN ("fr","en")) .
}} LIMIT {limit}
""".strip()

# --- GÉNÉRATEUR CLUB -> STADE ---
def build_sparql_club_stadium(club_name: str, limit: int = 10) -> str:
    safe = _safe_contains(club_name)
    return f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dbo:  <http://dbpedia.org/ontology/>
SELECT DISTINCT ?clubLabel ?stadiumName ?cap WHERE {{
  ?club a dbo:SoccerClub ; rdfs:label ?clubLabel .
  FILTER(lang(?clubLabel) IN ("fr","en")) .
  BIND(LCASE(STR(?clubLabel)) AS ?lbl)
  FILTER(CONTAINS(?lbl, "{safe}"))
  
  # Filtres anti-réserves et féminines renforcés
  FILTER(!REGEX(?lbl, "castilla|youth|reserves|femen|fémin|\\\\b(b|ii|u\\\\d{{1,2}})\\\\b"))

  OPTIONAL {{ 
    ?club dbo:ground ?s . 
    ?s rdfs:label ?stadiumName . 
    FILTER(lang(?stadiumName) IN ("fr","en")) 
  }}
  OPTIONAL {{ ?club dbo:capacity ?cap }}

  # Scoring : Si le nom est exactement le nom cherché, on lui donne la priorité
  BIND(IF(?lbl = "{safe}", 2, 1) AS ?score)
}} ORDER BY DESC(?score) LIMIT {limit}
""".strip()

# --- FORMATEUR DE RÉPONSES ---
def format_answer(intent: str, entity: str, rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return f"Je n'ai pas trouvé d'informations pour **{entity}**."
    
    # On prend la première ligne (la mieux scorée par le SPARQL)
    top = rows[0]
    
    if intent == "club_stadium":
        stade = top.get('stadiumName')
        # Si le stade trouvé est juste "Spain" ou vide, on gère proprement
        if not stade or stade.lower() == "spain":
            return f"J'ai trouvé le club **{top['clubLabel']}**, mais son stade n'est pas précisé dans DBpedia."
        
        capa = f" (capacité: {top['cap']})" if top.get('cap') else ""
        return f"Le stade de **{top['clubLabel']}** est **{stade}**{capa}."
    else:
        # On regroupe les clubs uniques
        clubs = sorted(list(set(r.get("clubLabel") for r in rows if r.get("clubLabel"))))
        return f"**{entity}** est associé aux clubs suivants : " + ", ".join(f"**{c}**" for c in clubs)