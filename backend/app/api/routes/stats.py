"""Aggregate statistics used by the landing page and dashboard."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DbSession, EventServiceDep
from app.api.schemas import (
    EmbedderOut,
    FacetValue,
    FacetsOut,
    RunOut,
    StatsOverviewOut,
    TimelineDayOut,
)
from app.api.serializers import run_payload
from app.database.models import Article, Event, IngestionRun, Publisher, utcnow
from app.ml.embeddings import embedding_service
from app.services.event_service import EventService

router = APIRouter(tags=["stats"])


def _embedder() -> EmbedderOut:
    info = embedding_service.info
    return EmbedderOut(
        model=info.model,
        dim=info.dim,
        semantic=info.semantic,
        backend="sentence-transformers" if info.semantic else "hashing-fallback",
    )


@router.get("/stats/overview", response_model=StatsOverviewOut)
def overview(db: DbSession, service: EventServiceDep) -> StatsOverviewOut:
    now = utcnow()
    day_ago = now - timedelta(hours=24)

    events_total = int(db.scalar(select(func.count(Event.id))) or 0)
    multi_source = int(db.scalar(select(func.count(Event.id)).where(Event.publisher_count >= 2)) or 0)
    articles_total = int(db.scalar(select(func.count(Article.id))) or 0)
    publishers_total = int(db.scalar(select(func.count(Publisher.id))) or 0)
    publishers_reporting = int(
        db.scalar(select(func.count(func.distinct(Article.publisher_id)))) or 0
    )
    events_last_24h = int(
        db.scalar(select(func.count(Event.id)).where(Event.last_published_at >= day_ago)) or 0
    )
    articles_last_24h = int(
        db.scalar(select(func.count(Article.id)).where(Article.published_at >= day_ago)) or 0
    )
    avg_publishers = float(
        db.scalar(select(func.avg(Event.publisher_count)).where(Event.publisher_count > 0)) or 0.0
    )

    distribution = {"1": 0, "2": 0, "3-4": 0, "5+": 0}
    rows = db.execute(
        select(Event.publisher_count, func.count(Event.id)).group_by(Event.publisher_count)
    ).all()
    for count, total in rows:
        count = int(count or 0)
        if count <= 1:
            distribution["1"] += int(total)
        elif count == 2:
            distribution["2"] += int(total)
        elif count <= 4:
            distribution["3-4"] += int(total)
        else:
            distribution["5+"] += int(total)

    categories = [
        FacetValue(value=name, label=name, count=count) for name, count in service.category_counts()
    ]
    latest_run = db.scalar(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1))

    return StatsOverviewOut(
        events_total=events_total,
        multi_source_events=multi_source,
        single_source_events=max(0, events_total - multi_source),
        articles_total=articles_total,
        publishers_total=publishers_total,
        publishers_reporting=publishers_reporting,
        events_last_24h=events_last_24h,
        articles_last_24h=articles_last_24h,
        avg_publishers_per_event=round(avg_publishers, 2),
        coverage_distribution=distribution,
        categories=categories,
        embedder=_embedder(),
        latest_run=RunOut(**run_payload(latest_run)) if latest_run else None,
        generated_at=now,
    )


@router.get("/stats/timeline", response_model=list[TimelineDayOut])
def timeline(db: DbSession, days: int = 14) -> list[TimelineDayOut]:
    days = max(1, min(days, 60))
    cutoff = utcnow() - timedelta(days=days)
    event_rows = db.execute(
        select(func.date(Event.last_published_at), func.count(Event.id))
        .where(Event.last_published_at >= cutoff)
        .group_by(func.date(Event.last_published_at))
    ).all()
    article_rows = db.execute(
        select(func.date(Article.published_at), func.count(Article.id))
        .where(Article.published_at >= cutoff)
        .group_by(func.date(Article.published_at))
    ).all()
    events_by_day = {str(row[0]): int(row[1]) for row in event_rows}
    articles_by_day = {str(row[0]): int(row[1]) for row in article_rows}
    today = utcnow().date()
    output: list[TimelineDayOut] = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        key = day.isoformat()
        output.append(
            TimelineDayOut(
                date=key, events=events_by_day.get(key, 0), articles=articles_by_day.get(key, 0)
            )
        )
    return output


@router.get("/stats/facets", response_model=FacetsOut)
def facets(db: DbSession, service: EventServiceDep) -> FacetsOut:
    categories = [
        FacetValue(value=name, label=name, count=count) for name, count in service.category_counts()
    ]
    publisher_rows = dict(EventService(db).publisher_counts())
    publishers = list(db.scalars(select(Publisher).order_by(Publisher.name)).all())
    publisher_facets = [
        FacetValue(
            value=publisher.id,
            label=publisher.short_name,
            count=int(publisher_rows.get(publisher.id, 0)),
        )
        for publisher in publishers
        if publisher.enabled or publisher.id in publisher_rows
    ]
    publisher_facets.sort(key=lambda facet: (-facet.count, facet.label))
    return FacetsOut(categories=categories, publishers=publisher_facets)
