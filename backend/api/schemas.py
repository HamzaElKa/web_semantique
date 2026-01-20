from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

EndpointName = Literal["dbpedia", "wikidata"]
EntityType = Literal["player", "club", "stadium"]


class ApiMeta(BaseModel):
    endpoint: EndpointName
    limit: int
    cached: bool = False

    model_config = {"extra": "forbid"}


class SearchResultItem(BaseModel):
    uri: str
    label: str
    description: Optional[str] = None
    type: Optional[EntityType] = None

    model_config = {"extra": "forbid"}


class SearchResponse(BaseModel):
    meta: ApiMeta
    query: str
    entity_type: EntityType
    results: List[SearchResultItem]

    model_config = {"extra": "forbid"}


class EntityResponse(BaseModel):
    meta: ApiMeta
    uri: str
    label: Optional[str] = None
    facts: Dict[str, Any] = Field(default_factory=dict)
    neighbors: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class GraphResponse(BaseModel):
    meta: ApiMeta
    seed_uri: str
    depth: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

    model_config = {"extra": "forbid"}


class SimilarityResponse(BaseModel):
    meta: ApiMeta
    entity_type: EntityType
    uri: str
    similar: List[Dict[str, Any]]

    model_config = {"extra": "forbid"}


class AskRequest(BaseModel):
    question: str
    endpoint: Optional[EndpointName] = None

    model_config = {"extra": "forbid"}


class AskResponse(BaseModel):
    meta: ApiMeta
    question: str
    generated_sparql: str
    rows: List[Dict[str, Any]]
    answer: str

    model_config = {"extra": "forbid"}



class ExplainGraphRequest(BaseModel):
    seed_uri: str
    metrics: Dict[str, Any]              # la réponse de /graph/metrics
    example_edges: Optional[List[Dict[str, str]]] = None  # optionnel
    lang: str = "fr"

class ExplainGraphResponse(BaseModel):
    explanation: str
    provider: str
