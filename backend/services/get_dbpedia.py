from __future__ import annotations

from typing import Any, Dict, List, Optional
import time
import logging

from SPARQLWrapper import SPARQLWrapper, JSON

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    def _run(self, query: str, retries: int = 3) -> List[Dict[str, Any]]:
        attempt = 0
        while attempt < retries:
            try:
                self.sparql.setQuery(query)
                results = self.sparql.query().convert()
                bindings = results.get("results", {}).get("bindings", [])
                return bindings if isinstance(bindings, list) else []
            except Exception as e:
                attempt += 1
                logger.warning(f"Tentative {attempt}/{retries} échouée : {e}")
                if attempt < retries:
                    time.sleep(2)
                else:
                    return []
        return []

    def get_specific_clubs(self, lang: str = "fr") -> List[Dict[str, Any]]:
        """
        CORRECTION ICI : Utilisation des URIs complètes <...> pour PSG et City
        car le point final de 'F.C.' casse la syntaxe SPARQL s'il est utilisé avec 'dbr:'.
        """
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
                ?uri dbo:ground ?stade .
                ?stade rdfs:label ?stadeLabel .
                FILTER(lang(?stadeLabel) = '{lang}')
                OPTIONAL {{ ?stade dbo:capacity ?capacite }}
            }}

            OPTIONAL {{ ?uri dbo:thumbnail ?img }}
        }}
        """
        bindings = self._run(query)
        
        clubs = []
        for item in bindings:
            clubs.append({
                "nom": item.get("nom", {}).get("value"),
                "stade": item.get("stadeLabel", {}).get("value", "Stade inconnu"),
                "capacite": item.get("capacite", {}).get("value", "N/A"),
                "image": item.get("img", {}).get("value", "https://via.placeholder.com/150")
            })
        return clubs

    def get_specific_players(self, lang: str = "fr") -> List[Dict[str, Any]]:
        """
        Nettoyage : On utilise GROUP BY pour n'avoir qu'une seule ligne par joueur.
        """
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dbp: <http://dbpedia.org/property/>

        SELECT ?uri (SAMPLE(?finalName) as ?nom) (SAMPLE(?clubLabel) as ?club) (SAMPLE(?img) as ?image) WHERE {{
            VALUES ?uri {{ 
                dbr:Lionel_Messi 
                dbr:Cristiano_Ronaldo 
                dbr:Neymar 
                dbr:Lamine_Yamal 
                dbr:Zinedine_Zidane 
            }}

            # 1. Nom : On prend le français, sinon l'anglais, sinon l'URI
            OPTIONAL {{ ?uri rdfs:label ?labelFR . FILTER(lang(?labelFR) = 'fr') }}
            OPTIONAL {{ ?uri rdfs:label ?labelEN . FILTER(lang(?labelEN) = 'en') }}
            BIND(COALESCE(?labelFR, ?labelEN, STR(?uri)) AS ?finalName)

            # 2. Club : On essaie de trouver un club (actuel ou passé)
            OPTIONAL {{ 
                ?uri (dbo:currentTeam|dbo:team|dbp:currentclub) ?team .
                ?team rdfs:label ?clubLabel .
                FILTER(lang(?clubLabel) = '{lang}')
            }}

            OPTIONAL {{ ?uri dbo:thumbnail ?img }}
        }}
        GROUP BY ?uri
        """
        bindings = self._run(query)
        
        joueurs = []
        for item in bindings:
            joueurs.append({
                "nom": item.get("nom", {}).get("value"),
                # Si le club est vide (cas fréquent pour Zidane retraité), on met un texte par défaut
                "club": item.get("club", {}).get("value", "Légende / Retraité"),
                "image": item.get("image", {}).get("value", "https://via.placeholder.com/150")
            })
        return joueurs

    def get_specific_clubs(self, lang: str = "fr") -> List[Dict[str, Any]]:
        """
        Correction : On enlève le filtre de langue strict sur le STADE pour éviter "Stade inconnu"
        si le nom n'existe qu'en anglais ou espagnol.
        """
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
                ?uri dbo:ground ?ground .
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
        
        comps = []
        for item in bindings:
            comps.append({
                "nom": item.get("nom", {}).get("value"),
                "pays": item.get("pays", {}).get("value", "Europe"),
                "image": item.get("image", {}).get("value", "https://via.placeholder.com/150")
            })
        return comps
# --- TEST ---
if __name__ == "__main__":
    service = DBpediaService()
    
    print("\n--- CLUBS (Test Correctif) ---")
    clubs = service.get_specific_clubs()
    for c in clubs:
        print(f" > {c['nom']} - {c['stade']}")

    print("\n--- JOUEURS ---")
    joueurs = service.get_specific_players()
    for p in joueurs:
        print(f" > {p['nom']} ({p['club']})")
    
    print("\n--- COMPETITIONS ---")
    comps = service.get_top_competitions()
    for c in comps:
        print(f" > {c['nom']}")
dbpedia_service = DBpediaService()
