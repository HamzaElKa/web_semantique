from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from api.schemas import GraphResponse, ApiMeta
from api.config import settings
from api.deps import get_sparql_client
from services.sparql_client import SparqlClient
from services.normalize import sparql_json_to_rows
import networkx as nx

router = APIRouter(prefix="/graph", tags=["graph"])

try:
    import community as community_louvain  # python-louvain
except Exception:
    community_louvain = None


def _validate_uri(u: str) -> str:
    u = (u or "").strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        raise HTTPException(status_code=400, detail="seed must be a valid http(s) URI")
    if any(x in u for x in ["<", ">", "{", "}", '"', "'"]):
        raise HTTPException(status_code=400, detail="seed contains invalid characters")
    return u


def _add_node(nodes_map: Dict[str, Dict[str, Any]], uri: str, label: Optional[str]) -> None:
    if uri not in nodes_map:
        nodes_map[uri] = {"id": uri, "label": label or uri}


@router.get("", response_model=GraphResponse)
async def graph(
    seed: str = Query(..., description="Seed entity URI (http(s))"),
    depth: int = Query(1, ge=1, le=2, description="1 or 2 hops (2 hops may be heavier)"),
    limit: int = Query(80, ge=1, le=settings.MAX_LIMIT),
    sparql: SparqlClient = Depends(get_sparql_client),
    mode: str = Query("generic", description="generic | foot"),
):
    seed_uri = _validate_uri(seed)

    # Foot-only filter (DBpedia predicates only)
    foot_filter = ""
    if mode.lower() == "foot":
        foot_filter = """
    FILTER (?p IN (
        <http://dbpedia.org/ontology/team>,
        <http://dbpedia.org/ontology/club>,
        <http://dbpedia.org/ontology/currentTeam>,
        <http://dbpedia.org/ontology/nationalteam>,
        <http://dbpedia.org/ontology/position>,
        <http://dbpedia.org/ontology/league>,
        <http://dbpedia.org/ontology/ground>,
        <http://dbpedia.org/ontology/manager>,
        <http://dbpedia.org/ontology/award>,
        <http://dbpedia.org/ontology/birthPlace>
    ))
    """.rstrip()

    # 1-hop query
    query_1 = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT
  ?s
  (SAMPLE(?sLabel) AS ?sLabel)
  ?p
  (SAMPLE(?pLabel) AS ?pLabel)
  ?o
  (SAMPLE(?oLabel) AS ?oLabel)
WHERE {{
  BIND(<{seed_uri}> AS ?s)
  ?s ?p ?o .
  {foot_filter}

  FILTER(isIRI(?o))

  OPTIONAL {{ ?s rdfs:label ?sLabel . FILTER(lang(?sLabel) IN ("en","fr")) }}
  OPTIONAL {{ ?p rdfs:label ?pLabel . FILTER(lang(?pLabel) IN ("en","fr")) }}
  OPTIONAL {{ ?o rdfs:label ?oLabel . FILTER(lang(?oLabel) IN ("en","fr")) }}
}}
GROUP BY ?s ?p ?o
LIMIT {limit}
""".strip()

    data1 = await sparql.query(query=query_1, endpoint="dbpedia", limit=limit, use_cache=True)
    rows1 = sparql_json_to_rows(data1)

    nodes_map: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    # Build 1-hop graph
    one_hop_targets: List[str] = []
    for r in rows1:
        s = r.get("s")
        o = r.get("o")
        if not s or not o:
            continue

        p_label = r.get("pLabel") or r.get("p") or ""
        s_label = r.get("sLabel") or s
        o_label = r.get("oLabel") or o

        _add_node(nodes_map, s, s_label)
        _add_node(nodes_map, o, o_label)
        edges.append({"source": s, "target": o, "label": p_label})

        if isinstance(o, str) and (o.startswith("http://") or o.startswith("https://")):
            one_hop_targets.append(o)

    # Optional 2-hop expansion (lightweight): expand a small subset of targets
    if depth == 2 and one_hop_targets:
        max_targets = 15
        targets = one_hop_targets[:max_targets]
        limit2 = min(200, settings.MAX_LIMIT)
        values = " ".join(f"<{t}>" for t in targets)

        query_2 = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT
  ?s
  (SAMPLE(?sLabel) AS ?sLabel)
  ?p
  (SAMPLE(?pLabel) AS ?pLabel)
  ?o
  (SAMPLE(?oLabel) AS ?oLabel)
WHERE {{
  VALUES ?s {{ {values} }}
  ?s ?p ?o .
  {foot_filter}

  FILTER(isIRI(?o))

  OPTIONAL {{ ?s rdfs:label ?sLabel . FILTER(lang(?sLabel) IN ("en","fr")) }}
  OPTIONAL {{ ?p rdfs:label ?pLabel . FILTER(lang(?pLabel) IN ("en","fr")) }}
  OPTIONAL {{ ?o rdfs:label ?oLabel . FILTER(lang(?oLabel) IN ("en","fr")) }}
}}
GROUP BY ?s ?p ?o
LIMIT {limit2}
""".strip()

        data2 = await sparql.query(query=query_2, endpoint="dbpedia", limit=limit2, use_cache=True)
        rows2 = sparql_json_to_rows(data2)

        for r in rows2:
            s = r.get("s")
            o = r.get("o")
            if not s or not o:
                continue

            p_label = r.get("pLabel") or r.get("p") or ""
            s_label = r.get("sLabel") or s
            o_label = r.get("oLabel") or o

            _add_node(nodes_map, s, s_label)
            _add_node(nodes_map, o, o_label)
            edges.append({"source": s, "target": o, "label": p_label})

    # Cap edges to keep response small
    if len(edges) > 2000:
        edges = edges[:2000]

    return GraphResponse(
        meta=ApiMeta(endpoint="dbpedia", limit=limit, cached=False),
        seed_uri=seed_uri,
        depth=depth,
        nodes=list(nodes_map.values()),
        edges=edges,
    )


@router.get("/metrics")
async def graph_metrics(
    seed: str = Query(...),
    depth: int = Query(1, ge=1, le=2),
    limit: int = Query(80, ge=1, le=settings.MAX_LIMIT),
    sparql: SparqlClient = Depends(get_sparql_client),
):
    # Reuse graph existing endpoint (DBpedia-only) in "foot" mode
    g = await graph(seed=seed, depth=depth, limit=limit, sparql=sparql, mode="foot")

    nodes = g.nodes
    edges = g.edges

    # Build NetworkX graph (undirected for structural centralities)
    G = nx.Graph()
    for n in nodes:
        G.add_node(n["id"], label=n.get("label") or n["id"])
    for e in edges:
        G.add_edge(e["source"], e["target"], label=e.get("label") or "")

    if G.number_of_nodes() == 0:
        return {"seed_uri": seed, "n_nodes": 0, "n_edges": 0}

    degree = dict(G.degree())
    pagerank = nx.pagerank(G, alpha=0.85) if G.number_of_nodes() <= 500 else {}
    betweenness = (
        nx.betweenness_centrality(G, k=min(80, G.number_of_nodes()), seed=42) if G.number_of_nodes() > 5 else {}
    )

    communities = {}
    if community_louvain is not None and G.number_of_nodes() > 3:
        communities = community_louvain.best_partition(G, random_state=42)

    def top_k(d, k=10):
        items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:k]
        out = []
        for node_id, score in items:
            out.append({"id": node_id, "label": G.nodes[node_id].get("label", node_id), "score": float(score)})
        return out

    comps = nx.number_connected_components(G)
    density = nx.density(G)

    return {
        "seed_uri": g.seed_uri,
        "depth": g.depth,
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "stats": {"density": float(density), "components": int(comps)},
        "top_degree": top_k(degree, 10),
        "top_pagerank": top_k(pagerank, 10) if pagerank else [],
        "top_betweenness": top_k(betweenness, 10) if betweenness else [],
        "communities": communities,
    }
