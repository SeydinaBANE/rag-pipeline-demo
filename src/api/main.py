from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import feedback, health, ingest, metrics, query
from src.config import get_settings


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="RAG Pipeline API",
        version=s.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, tags=["health"])
    app.include_router(metrics.router, tags=["metrics"])
    app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
    app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["ingest"])
    app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])

    return app


app = create_app()
