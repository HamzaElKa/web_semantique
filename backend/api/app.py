from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes_explain import router as explain_router

from api.config import settings

# DBpedia-only routes
from api.routes_dbpedia_foot import router as dbpedia_foot_router
from api.routes_search import router as search_router
from api.routes_entity import router as entity_router
from api.routes_graph import router as graph_router
from api.routes_similarity import router as similarity_router
from api.routes_ask import router as ask_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="4IF-WS Foot Explorer API (DBpedia-only)",
        version="1.0.0",
        description="API for exploring football entities using DBpedia SPARQL + graph endpoints.",
    )

    # CORS
    # Optionnel: ajoute CORS_ORIGINS dans .env: "http://localhost:5500,http://127.0.0.1:5500"
    origins = getattr(settings, "CORS_ORIGINS", "")
    allow_origins = [o.strip() for o in origins.split(",") if o.strip()] or ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(dbpedia_foot_router)
    app.include_router(search_router)
    app.include_router(entity_router)
    app.include_router(graph_router)
    app.include_router(similarity_router)
    app.include_router(ask_router)

    @app.get("/", tags=["meta"])
    async def root():
        return {
            "name": app.title,
            "version": app.version,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
            "routes": {
                "dbpedia_home": "/dbpedia-foot/home?lang=fr",
                "dbpedia_players": "/dbpedia-foot/players?lang=fr",
                "dbpedia_clubs": "/dbpedia-foot/clubs?lang=fr",
                "dbpedia_competitions": "/dbpedia-foot/competitions?lang=fr",
                "search": "/search?q=messi&entity_type=player&limit=10",
                "entity": "/entity?id=http://dbpedia.org/resource/Lionel_Messi&limit=30",
                "graph": "/graph?seed=http://dbpedia.org/resource/Lionel_Messi&limit=50",
            },
        }

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok"}

    return app
app = create_app()
app.include_router(explain_router)