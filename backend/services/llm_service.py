import json
from openai import OpenAI
from api.config import settings

# On configure le client pour taper sur Ollama en local
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Requis par la librairie mais ignoré par Ollama
)

def analyze_football_intent(question: str) -> dict:
    """
    Analyse la question via Ollama (Mistral/Llama3).
    """
    prompt = f"""
    Tu es un expert en football. Analyse cette question : "{question}"
    Réponds uniquement au format JSON strict :
    {{
      "intent": "player_club" ou "club_stadium",
      "entity": "nom du joueur ou club extrait"
    }}
    """
    try:
        response = client.chat.completions.create(
            model="mistral", # Assure-toi d'avoir fait 'ollama run mistral'
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Erreur Ollama : {e}")
        # Fallback si Ollama n'est pas lancé
        is_stadium = any(w in question.lower() for w in ["stade", "stadium", "ground"])
        return {
            "intent": "club_stadium" if is_stadium else "player_club",
            "entity": question
        }