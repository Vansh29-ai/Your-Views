"""Publisher endpoints, including live feed health."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.api.schemas import PublisherDetail
from app.api.serializers import iso
from app.database.models import Article, FeedHealth, Publisher
from app.services.event_service import EventService

router = APIRouter(prefix="/publishers", tags=["publishers"])


def _publisher_payload(publisher: Publisher, health: list[FeedHealth], article_count: int,
                       event_count: int, last_published) -> dict:  # type: ignore[no-untyped-def]
    return {
        "id": publisher.id,
        "name": publisher.name,
        "short_name": publisher.short_name,
        "country": publisher.country,
        "tier": publisher.tier,
        "accent": publisher.accent,
        "access": publisher.access,
        "homepage": publisher.homepage,
        "feed_count": publisher.feed_count,
        "enabled": publisher.enabled,
        "unavailable_reason": publisher.unavailable_reason,
        "article_count": article_count,
        "event_count": event_count,
        "last_published_at": iso(last_published),
        "feeds": [
            {
                "feed_id": row.feed_id,
                "url": row.url,
                "category": row.category,
                "status": row.status,
                "http_status": row.http_status,
                "latency_ms": row.latency_ms,
                "last_checked_at": iso(row.last_checked_at),
                "last_success_at": iso(row.last_success_at),
                "consecutive_failures": row.consecutive_failures,
                "error": row.error,
                "items_last_fetch": row.items_last_fetch,
            }
            for row in health
        ],
    }


@router.get("", response_model=list[PublisherDetail])
def list_publishers(db: DbSession) -> list[PublisherDetail]:
    publishers = list(db.scalars(select(Publisher).order_by(Publisher.name)).all())
    health_rows = db.scalars(select(FeedHealth)).all()
    health_by_publisher: dict[str, list[FeedHealth]] = {}
    for row in health_rows:
        health_by_publisher.setdefault(row.publisher_id, []).append(row)

    article_counts = dict(
        db.execute(
            select(Article.publisher_id, func.count(Article.id)).group_by(Article.publisher_id)
        ).all()
    )
    last_article = dict(
        db.execute(
            select(Article.publisher_id, func.max(Article.published_at)).group_by(Article.publisher_id)
        ).all()
    )
    event_counts = dict(EventService(db).publisher_counts())

    return [
        PublisherDetail(
            **_publisher_payload(
                publisher,
                health_by_publisher.get(publisher.id, []),
                int(article_counts.get(publisher.id, 0)),
                int(event_counts.get(publisher.id, 0)),
                last_article.get(publisher.id),
            )
        )
        for publisher in publishers
    ]


@router.get("/{publisher_id}", response_model=PublisherDetail)
def get_publisher(publisher_id: str, db: DbSession) -> PublisherDetail:
    publisher = db.get(Publisher, publisher_id)
    if publisher is None:
        raise HTTPException(status_code=404, detail="Publisher not found")
    rows = db.scalars(select(FeedHealth).where(FeedHealth.publisher_id == publisher_id)).all()
    article_count = int(
        db.scalar(select(func.count(Article.id)).where(Article.publisher_id == publisher_id)) or 0
    )
    last_published = db.scalar(
        select(func.max(Article.published_at)).where(Article.publisher_id == publisher_id)
    )
    event_count = int(dict(EventService(db).publisher_counts()).get(publisher_id, 0))
    return PublisherDetail(
        **_publisher_payload(publisher, list(rows), article_count, event_count, last_published)
    )
