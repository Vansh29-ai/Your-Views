"""Health endpoint used by the UI status strip and deployment probes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.api.schemas import EmbedderOut, HealthOut
from app.database.models import FeedHealth, IngestionRun
from app.ml.embeddings import embedding_service
from app.services.search_service import fts_available

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health(db: DbSession) -> HealthOut:
    database_ok = True
    try:
        db.execute(select(func.count()).select_from(IngestionRun))
    except Exception:
        database_ok = False

    feed_count = int(db.scalar(select(func.count(FeedHealth.feed_id))) or 0)
    healthy = int(
        db.scalar(select(func.count(FeedHealth.feed_id)).where(FeedHealth.status == "ok")) or 0
    )
    latest_run = db.scalar(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1))
    info = embedding_service.info
    status = "ok" if database_ok and healthy > 0 else "degraded"

    return HealthOut(
        status=status,
        database=database_ok,
        fts=fts_available(),
        embedder=EmbedderOut(
            model=info.model,
            dim=info.dim,
            semantic=info.semantic,
            backend="sentence-transformers" if info.semantic else "hashing-fallback",
        ),
        feeds_total=feed_count,
        feeds_healthy=healthy,
        last_run_status=latest_run.status if latest_run else None,
        version="1.0.0",
    )
