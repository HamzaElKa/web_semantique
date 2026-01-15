from __future__ import annotations

from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


def pick_label(binding: Dict[str, Any], fallback_key: str = "uri") -> str:
    """
    Pick a human-readable label from a SPARQL binding.
    """
    try:
        label = binding.get("label")
        if isinstance(label, dict) and "value" in label:
            return str(label["value"])

        fallback = binding.get(fallback_key)
        if isinstance(fallback, dict) and "value" in fallback:
            return str(fallback["value"])
    except Exception:
        pass

    return ""


def to_row(binding: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a SPARQL binding object into a flat dict { var: value }.
    """
    row: Dict[str, Any] = {}

    for key, value in binding.items():
        if isinstance(value, dict):
            # Standard SPARQL JSON format
            if "value" in value:
                row[key] = value["value"]
            else:
                # Unexpected structure → keep raw
                row[key] = value
        else:
            row[key] = value

    return row


def sparql_json_to_rows(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a SPARQL JSON response to a list of flat rows.
    Returns [] if the response is invalid or not SPARQL JSON.
    """
    if not isinstance(data, dict):
        logger.warning("Invalid SPARQL response type: %s", type(data))
        return []

    results = data.get("results")
    if not isinstance(results, dict):
        logger.warning("Missing 'results' in SPARQL response")
        return []

    bindings = results.get("bindings")
    if not isinstance(bindings, list):
        logger.warning("Missing 'bindings' in SPARQL response")
        return []

    return [to_row(b) for b in bindings if isinstance(b, dict)]
