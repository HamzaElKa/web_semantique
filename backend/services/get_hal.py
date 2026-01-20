from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import logging

from SPARQLWrapper import SPARQLWrapper, JSON

logger = logging.getLogger(__name__)


def _normalize_lang(lang: str) -> str:
    lang = (lang or "fr").strip().lower()
    return lang if lang in ("fr", "en") else "fr"


class HALService:
    """
    Minimal HAL SPARQL service, similar to DBpediaService.
    Endpoint: https://sparql.archives-ouvertes.fr/sparql
    """


    def __init__(self, endpoint: str = "https://sparql.archives-ouvertes.fr/sparql", timeout_s: int = 30):
        self.endpoint = endpoint
        self.sparql = SPARQLWrapper(endpoint)
        self.sparql.setReturnFormat(JSON)
        self.sparql.setTimeout(timeout_s)

        try:
            self.sparql.addCustomHttpHeader(
                "User-Agent",
                "4IF-WS-Foot-Explorer/1.0 (INSA Lyon; contact: student)",
            )
            self.sparql.addCustomHttpHeader("Accept", "application/sparql-results+json")
        except Exception:
            pass

    def _run(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a SPARQL query and return bindings.
        Returns [] on error (stable API), logs warning for debugging.
        """
        try:
            self.sparql.setQuery(query)
            results = self.sparql.query().convert()
            bindings = results.get("results", {}).get("bindings", [])
            return bindings if isinstance(bindings, list) else []
        except Exception as e:
            logger.warning("HAL query failed: %s", e)
            return []

    # ---------------------------
    # 1) Exploration / Debug
    # ---------------------------
    def list_graphs(self, limit: int = 50) -> List[Dict[str, Optional[str]]]:
        """
        List named graphs present in the endpoint (useful to understand dataset structure).
        """
        limit = max(1, min(int(limit), 200))

        query = f"""
SELECT DISTINCT ?g (COUNT(*) AS ?triples)
WHERE {{
  GRAPH ?g {{ ?s ?p ?o }}
}}
GROUP BY ?g
ORDER BY DESC(?triples)
LIMIT {limit}
""".strip()

        bindings = self._run(query)
        out: List[Dict[str, Optional[str]]] = []
        for b in bindings:
            g = b.get("g", {}).get("value")
            triples = b.get("triples", {}).get("value")
            out.append({"graph": g, "triples": triples})
        return out

    def describe_predicates_for_doc(self, doc_iri: str, limit: int = 200) -> List[Dict[str, Optional[str]]]:
        """
        Debug helper: given a HAL document IRI, list predicates used on it.
        Use this to discover the correct property for "document -> author".
        """
        limit = max(1, min(int(limit), 500))
        doc_iri = (doc_iri or "").strip()
        if not doc_iri.startswith("http"):
            return []

        query = f"""
SELECT ?p ?o
WHERE {{
  <{doc_iri}> ?p ?o
}}
LIMIT {limit}
""".strip()

        bindings = self._run(query)
        out: List[Dict[str, Optional[str]]] = []
        for b in bindings:
            out.append(
                {
                    "p": b.get("p", {}).get("value"),
                    "o": b.get("o", {}).get("value"),
                }
            )
        return out

    # ---------------------------
    # 2) Simple author lookup
    # ---------------------------
    def search_authors_by_topic_interest(
        self, topic: str = "RDF", limit: int = 200
    ) -> List[Dict[str, Optional[str]]]:
        """
        Find authors having foaf:topic_interest "RDF" (example often used in HAL docs).
        """
        topic = (topic or "").strip()
        if not topic:
            return []
        limit = max(1, min(int(limit), 500))

        query = f"""
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

SELECT DISTINCT ?person ?name
WHERE {{
  ?person a foaf:Person ;
          foaf:topic_interest "{topic}" ;
          foaf:name ?name .
}}
LIMIT {limit}
""".strip()

        bindings = self._run(query)
        out: List[Dict[str, Optional[str]]] = []
        for b in bindings:
            out.append(
                {
                    "person": b.get("person", {}).get("value"),
                    "name": b.get("name", {}).get("value"),
                }
            )
        return out

    # ---------------------------
    # 3) Co-author network (edges)
    # ---------------------------
    def get_coauthors_network(
        self,
        min_shared_pubs: int = 2,
        limit: int = 500,
        use_creator_predicate: str = "http://purl.org/dc/terms/creator",
    ) -> List[Dict[str, Optional[str]]]:
        """
        Build a co-author edge list:
          - a1 (IRI), a1Name
          - a2 (IRI), a2Name
          - w = number of shared documents

        By default uses dcterms:creator. If HAL uses another predicate, pass it via use_creator_predicate
        after discovering it with describe_predicates_for_doc().
        """
        min_shared_pubs = max(1, int(min_shared_pubs))
        limit = max(1, min(int(limit), 2000))
        pred = (use_creator_predicate or "").strip()
        if not pred.startswith("http"):
            return []

        query = f"""
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

SELECT ?a1 ?a1Name ?a2 ?a2Name (COUNT(DISTINCT ?doc) AS ?w)
WHERE {{
  ?doc <{pred}> ?a1, ?a2 .
  FILTER(?a1 != ?a2)

  OPTIONAL {{ ?a1 foaf:name ?a1Name . }}
  OPTIONAL {{ ?a2 foaf:name ?a2Name . }}
}}
GROUP BY ?a1 ?a1Name ?a2 ?a2Name
HAVING(COUNT(DISTINCT ?doc) >= {min_shared_pubs})
ORDER BY DESC(?w)
LIMIT {limit}
""".strip()

        bindings = self._run(query)
        edges: List[Dict[str, Optional[str]]] = []

        for b in bindings:
            a1 = b.get("a1", {}).get("value")
            a2 = b.get("a2", {}).get("value")
            w = b.get("w", {}).get("value")

            # Names might be missing => keep IRIs as fallback
            a1_name = b.get("a1Name", {}).get("value") or a1
            a2_name = b.get("a2Name", {}).get("value") or a2

            if not a1 or not a2:
                continue

            edges.append(
                {
                    "a1": a1,
                    "a1Name": a1_name,
                    "a2": a2,
                    "a2Name": a2_name,
                    "weight": w,
                }
            )

        return edges


hal_service = HALService()
