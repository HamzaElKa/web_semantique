from __future__ import annotations
from fastapi import FastAPI
from api.routes_search import router as search_router
from api.routes_entity import router as entity_router
from api.routes_graph import router as graph_router
from api.routes_similarity import router as similarity_router
from api.routes_ask import router as ask_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="4IF-WS Foot Explorer API",
        version="1.0.0",
    )

    app.include_router(search_router)
    app.include_router(entity_router)
    app.include_router(graph_router)
    app.include_router(similarity_router)
    app.include_router(ask_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
