from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes_dbpedia_foot import router as dbpedia_foot_router


from api.config import settings
from api.routes_search import router as search_router
from api.routes_entity import router as entity_router
from api.routes_graph import router as graph_router
from api.routes_similarity import router as similarity_router
from api.routes_ask import router as ask_router
from api.routes_dbpedia import router as dbpedia_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="4IF-WS Foot Explorer API",
        version="1.0.0",
        description=(
            "API for exploring football entities with SPARQL (DBpedia/Wikidata), "
            "graph analysis and LLM-assisted queries."
        ),
    )

    # CORS: allow frontend to call the API (HTML/JS on another port).
    # You can set CORS_ORIGINS="http://localhost:5500,http://127.0.0.1:5500" in .env
    origins = getattr(settings, "CORS_ORIGINS", None)
    if origins:
        allow_origins = [o.strip() for o in origins.split(",") if o.strip()]
    else:
        allow_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(search_router)
    app.include_router(entity_router)
    app.include_router(graph_router)
    app.include_router(similarity_router)
    app.include_router(ask_router)
    app.include_router(dbpedia_router)
    app.include_router(dbpedia_foot_router)


    @app.get("/", tags=["meta"])
    async def root():
        return {
            "name": app.title,
            "version": app.version,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
            "routes": {
                "search": "/search",
                "entity": "/entity",
                "graph": "/graph",
                "similarity": "/similarity",
                "ask": "/ask",
                "dbpedia_stadiums": "/dbpedia/stadiums?city=London&lang=fr&limit=10",
                "dbpedia_psg": "/dbpedia/psg?lang=fr",
            },
        }

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok"}

    return app
