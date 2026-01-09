from __future__ import annotations
from typing import Any, Dict, List, Optional

def pick_label(binding: Dict[str, Any], fallback_key: str = "uri") -> str:
    # DBpedia/Wikidata often returns ?label
    if "label" in binding and "value" in binding["label"]:
        return str(binding["label"]["value"])
    if fallback_key in binding and "value" in binding[fallback_key]:
        return str(binding[fallback_key]["value"])
    return ""

def to_row(binding: Dict[str, Any]) -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    for k, v in binding.items():
        if isinstance(v, dict) and "value" in v:
            row[k] = v["value"]
        else:
            row[k] = v
    return row

def sparql_json_to_rows(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    bindings = data.get("results", {}).get("bindings", []) or []
    return [to_row(b) for b in bindings]