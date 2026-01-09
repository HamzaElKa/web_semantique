from SPARQLWrapper import SPARQLWrapper, JSON

# Initialisation de l'endpoint
sparql = SPARQLWrapper("http://dbpedia.org/sparql")

def get_stadiums_in_city(city):
    # On remplace les espaces par des underscores (ex: "San Francisco" -> "San_Francisco")
    city_resource = city.replace(" ", "_")
    
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
        FILTER (lang(?nomStade) = 'fr')
    }}
    ORDER BY DESC(?capacite)
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        bindings = results["results"]["bindings"]
        
        # On retourne une liste de tous les stades trouvés
        stades = []
        for item in bindings:
            stades.append({
                "nom": item["nomStade"]["value"],
                "capacite": item["capacite"]["value"]
            })
        return stades
    except Exception as e:
        print(f"Erreur requête ville : {e}")
        return []

# --- TEST DE LA FONCTION ---
print("Recherche des stades à Londres...")
stades_londres = get_stadiums_in_city("London")
for s in stades_londres:
    print(f"- {s['nom']} (Capacité: {s['capacite']})")

print("-" * 30)

# --- REQUÊTE PSG ---
query_psg = """
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dbp: <http://dbpedia.org/property/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?nom ?stadeLabel ?entraineurLabel
    WHERE {
        ?club a dbo:SoccerClub ;
              rdfs:label "Paris Saint-Germain F.C."@en ;
              dbo:ground ?stade ;
              dbo:manager ?entraineur .
        
        ?club rdfs:label ?nom .
        ?stade rdfs:label ?stadeLabel .
        ?entraineur rdfs:label ?entraineurLabel .

        FILTER (lang(?nom) = 'fr')
        FILTER (lang(?stadeLabel) = 'fr')
        FILTER (lang(?entraineurLabel) = 'fr')
    }
    LIMIT 1
"""

sparql.setQuery(query_psg)
sparql.setReturnFormat(JSON)

try:
    print("Envoi de la requête PSG...")
    results = sparql.query().convert()
    bindings = results["results"]["bindings"]

    for result in bindings:
        # Attention aux noms des clés ici !
        club = result["nom"]["value"]
        stade = result["stadeLabel"]["value"]
        coach = result["entraineurLabel"]["value"]
        print(f"Club : {club} | Stade : {stade} | Entraîneur : {coach}")

except Exception as e:
    print(f"Une erreur est survenue sur le PSG : {e}")