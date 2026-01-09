from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

EndpointName = Literal["dbpedia", "wikidata"]

class ApiMeta(BaseModel):
    endpoint: EndpointName
    limit: int
    cached: bool = False

class SearchResultItem(BaseModel):
    uri: str
    label: str
    description: Optional[str] = None
    type: Optional[str] = None

class SearchResponse(BaseModel):
    meta: ApiMeta
    query: str
    entity_type: str
    results: List[SearchResultItem]

class EntityResponse(BaseModel):
    meta: ApiMeta
    uri: str
    label: Optional[str] = None
    facts: Dict[str, Any] = Field(default_factory=dict)
    neighbors: List[Dict[str, Any]] = Field(default_factory=list)

class GraphResponse(BaseModel):
    meta: ApiMeta
    seed_uri: str
    depth: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

class SimilarityResponse(BaseModel):
    meta: ApiMeta
    entity_type: str
    uri: str
    similar: List[Dict[str, Any]]

class AskRequest(BaseModel):
    question: str
    endpoint: Optional[EndpointName] = None

class AskResponse(BaseModel):
    meta: ApiMeta
    question: str
    generated_sparql: str
    rows: List[Dict[str, Any]]
    answer: str
