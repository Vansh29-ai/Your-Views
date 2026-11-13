"""Admin/operations endpoints: ingestion control, runs, source registry, re-clustering."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.deps import DbSession, require_admin_key
from app.api.schemas import IngestStartOut, RunOut
from app.api.serializers import run_payload
from app.collectors.source_manager import source_manager
from app.database.models import FeedHealth, IngestionRun
from app.services.ingestion_service import ingestion_service
from app.services.recluster_service import recluster

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_key)])

_background_tasks: set[asyncio.Task] = set()


async def _run_ingestion(trigger: str) -> None:
    try:
        await ingestion_service.run(trigger)
    except Exception:  # pragma: no cover - already logged in the service
        logger.exception("Background ingestion failed")


@router.post("/ingest", response_model=IngestStartOut, status_code=202)
async def trigger_ingestion() -> IngestStartOut:
    if ingestion_service.is_running:
        return IngestStartOut(started=False, message="An ingestion run is already in progress.")
    task = asyncio.create_task(_run_ingestion("api"))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return IngestStartOut(
        started=True,
        message="Ingestion started. Poll /api/admin/status for progress.",
    )


@router.get("/status", response_model=dict)
def ingestion_status(db: DbSession) -> dict:
    latest = db.scalar(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1))
    health_rows = list(db.scalars(select(FeedHealth)).all())
    healthy = sum(1 for row in health_rows if row.status == "ok")
    return {
        "running": ingestion_service.is_running,
        "latest_run": run_payload(latest) if latest else None,
        "feeds_total": len(source_manager.feeds),
        "feeds_healthy": healthy,
        "publishers": len(source_manager.publishers),
        "load_error": source_manager.load_error,
    }


@router.get("/runs", response_model=list[RunOut])
def list_runs(db: DbSession, limit: int = Query(10, ge=1, le=50)) -> list[RunOut]:
    runs = db.scalars(
        select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
    ).all()
    return [RunOut(**run_payload(run)) for run in runs]


@router.get("/sources", response_model=list[dict])
def source_registry(db: DbSession) -> list[dict]:
    health = {row.feed_id: row for row in db.scalars(select(FeedHealth)).all()}
    payload = []
    for publisher in source_manager.publishers:
        payload.append(
            {
                "id": publisher.id,
                "name": publisher.name,
                "access": publisher.access,
                "available": publisher.available,
                "unavailable_reason": publisher.unavailable_reason,
                "feeds": [
                    {
                        "id": feed.id,
                        "url": feed.url,
                        "category": feed.display_category,
                        "status": health[feed.id].status if feed.id in health else "unknown",
                        "last_checked_at": health[feed.id].last_checked_at.isoformat() + "Z"
                        if feed.id in health and health[feed.id].last_checked_at
                        else None,
                        "error": health[feed.id].error if feed.id in health else None,
                    }
                    for feed in publisher.rss_feeds
                ],
            }
        )
    return payload


@router.post("/recluster", response_model=dict)
def run_recluster(
    db: DbSession,
    window_days: int = Query(7, ge=1, le=45),
    eps: float | None = Query(None, gt=0.0, lt=1.0),
    min_samples: int | None = Query(None, ge=2, le=10),
    algorithm: str = Query("dbscan", pattern="^(dbscan|agglomerative)$"),
) -> dict:
    if ingestion_service.is_running:
        raise HTTPException(status_code=409, detail="Cannot re-cluster while ingestion is running")
    try:
        return recluster(
            db, window_days=window_days, eps=eps, min_samples=min_samples, algorithm=algorithm
        )
    except Exception as exc:
        logger.exception("Re-clustering failed")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Re-clustering failed: {exc}") from exc
