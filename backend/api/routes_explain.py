from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import os
import httpx
import json
import re
from pydantic import BaseModel
from typing import Any, Dict


    


def parse_llm_json(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    cleaned = cleaned.replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response")
    return json.loads(cleaned[start:end+1])



router = APIRouter(prefix="/graph", tags=["llm"])

class ExplainGraphRequest(BaseModel):
    seed_uri: str
    metrics: Dict[str, Any]
    lang: str = "fr"

class ExplainGraphResponse(BaseModel):
    provider: str
    data: Dict[str, Any]

def build_prompt(req: ExplainGraphRequest) -> str:
    m = req.metrics or {}
    stats = m.get("stats", {}) or {}

    top_deg = (m.get("top_degree") or [])[:5]
    top_inf = (m.get("top_pagerank") or [])[:5]
    top_bt = (m.get("top_betweenness") or [])[:5]

    # communautés: tailles
    comm = m.get("communities", {}) or {}
    sizes = {}
    for _, cid in comm.items():
        sizes[cid] = sizes.get(cid, 0) + 1
    top_comms = sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:4]

    return f"""
Tu es un assistant d'analyse de graphes (niveau M1/école d'ingénieur).
Tu interprètes un graphe local (ego-network) construit depuis DBpedia via SPARQL autour d'une entité seed.
IMPORTANT : Ne fais pas de conclusions globales sur "le football mondial". Tu parles uniquement du graphe local.

Seed: {req.seed_uri}
Taille: {m.get("n_nodes",0)} noeuds, {m.get("n_edges",0)} liens
Structure: densité={stats.get("density")}, composantes={stats.get("components")}
Top hubs (degré): {top_deg}
Top influence (score): {top_inf}
Top ponts (betweenness): {top_bt}
Communautés (id, taille): {top_comms}

Format obligatoire (en {req.lang}):
1) Titre en 1 ligne.
2) "Ce que ça révèle" : 3 bullet points maximum.
3) "Limites" : 2 bullet points maximum (DBpedia bruit/incomplétude, choix des prédicats, graphe local).
4) "Suggestion" : 1 phrase d'action utilisateur (ex: changer seed, passer depth=2).

Ton style: clair, rigoureux, pas de blabla, pas de chiffres inutiles.
Tu dois répondre UNIQUEMENT en JSON valide (pas de markdown, pas de texte autour).

Schéma JSON STRICT :
{{
  "title": "string",
  "summary": "string (1-2 phrases)",
  "insights": ["bullet 1", "bullet 2", "bullet 3"],
  "limits": ["limit 1", "limit 2"],
  "next_steps": ["action 1", "action 2"]
}}

Contraintes:
- 3 insights max
- 2 limites max
- 2 next_steps max
- Ton analyse porte sur le graphe LOCAL autour de la seed, pas sur une vérité globale.
IMPORTANT: N'inclus PAS de balises ``` ni de markdown. Réponds uniquement avec un objet JSON brut.

""".strip()

@router.post("/explain", response_model=ExplainGraphResponse)
async def explain(req: ExplainGraphRequest):
    ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    prompt = build_prompt(req)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1) Try /api/chat
            r = await client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Tu interprètes des graphes de connaissances de façon rigoureuse."},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
            )

            if r.status_code == 200:
                data = r.json()
                text = ((data.get("message") or {}).get("content") or "").strip()
                if text:
                    obj = parse_llm_json(text)
                    return ExplainGraphResponse(provider=f"ollama:{model}", data=obj)

            # 2) Fallback /api/generate
            r2 = await client.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )

            if r2.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Ollama error: {r2.text}")

            data2 = r2.json()
            text2 = (data2.get("response") or "").strip()
            if not text2:
                raise HTTPException(status_code=502, detail="Empty response from Ollama")

            obj2 = parse_llm_json(text2)
            return ExplainGraphResponse(provider=f"ollama:{model}", data=obj2)

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Ollama not reachable: {e}")
    except Exception as e:
        # parse_llm_json / json.loads errors
        raise HTTPException(status_code=502, detail=f"LLM JSON parsing failed: {e}")
