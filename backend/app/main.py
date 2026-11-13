"""YOUR VIEWS — FastAPI application entrypoint.

Serves the JSON API under /api and, when a production frontend build exists, the compiled
React SPA from frontend/dist with client-side routing fallback.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import admin, events, health, news, publishers, search, stats
from app.config.settings import PROJECT_ROOT, settings
from app.database.init_db import init_db
from app.ml.embeddings import embedding_service
from app.services.scheduler import scheduler
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    init_db()
    logger.info("YOUR VIEWS API starting (env=%s)", settings.environment)
    if settings.enable_scheduler:
        scheduler.start()

    # Warm the embedding backend off the critical path; first ingestion benefits.
    import asyncio

    async def warmup() -> None:
        try:
            info = await asyncio.to_thread(embedding_service.warmup)
            logger.info("Embedding backend ready: %s (%sd, semantic=%s)", info.model, info.dim, info.semantic)
        except Exception:
            logger.exception("Embedding warmup failed; ingestion will retry lazily")

    warmup_task = asyncio.create_task(warmup())
    try:
        yield
    finally:
        warmup_task.cancel()
        await scheduler.stop()
        logger.info("YOUR VIEWS API stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="YOUR VIEWS API",
        description=(
            "Event-centric news intelligence: multi-publisher RSS ingestion, sentence embeddings, "
            "incremental event clustering and multi-perspective comparison."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=None,
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=800)

    api = APIRouter(prefix=settings.api_prefix)
    api.include_router(health.router)
    api.include_router(events.router)
    api.include_router(news.router)
    api.include_router(publishers.router)
    api.include_router(search.router)
    api.include_router(stats.router)
    api.include_router(admin.router)
    app.include_router(api)

    @app.exception_handler(SQLAlchemyError)
    async def _database_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error", exc_info=exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "The news store is temporarily unavailable. Please retry."},
        )

    if FRONTEND_DIST.exists():
        assets = FRONTEND_DIST / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str) -> FileResponse:
            if full_path.startswith(("api/", "api")):
                raise HTTPException(status_code=404, detail="Not found")
            candidate = (FRONTEND_DIST / full_path).resolve()
            if full_path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
                return FileResponse(candidate)
            index = FRONTEND_DIST / "index.html"
            if not index.exists():
                raise HTTPException(status_code=404, detail="Frontend build missing index.html")
            return FileResponse(index)
    else:
        @app.get("/", include_in_schema=False)
        def root() -> dict:
            return {
                "name": "YOUR VIEWS API",
                "status": "running",
                "docs": f"{settings.api_prefix}/docs",
                "frontend": "not built — run `pnpm build` in frontend/ or use the Vite dev server",
            }

    return app


app = create_app()
