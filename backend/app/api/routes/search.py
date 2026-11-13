"""Search endpoints — event-first results with article/publisher side results."""

from __future__ import annotations

import time

from fastapi import APIRouter, Query

from app.api.deps import DbSession, EventServiceDep
from app.api.schemas import SearchResultsOut
from app.api.serializers import PublisherDirectory, article_lite, event_list_item, publisher_lite
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResultsOut)
def search(
    db: DbSession,
    service: EventServiceDep,
    q: str = Query(..., min_length=2, max_length=160),
    limit: int = Query(8, ge=1, le=30),
    category: str | None = Query(None, max_length=60),
    publisher: str | None = Query(None, max_length=60),
) -> SearchResultsOut:
    started = time.perf_counter()
    directory = PublisherDirectory(db)
    search_service = SearchService(db)

    events, total = service.list_events(
        query=q,
        sort="relevance",
        page=1,
        page_size=limit,
        category=category,
        publisher=publisher,
    )
    leads = service.lead_articles(events)
    images = service.best_event_images(events)
    event_items = [
        event_list_item(
            event,
            directory,
            lead_article=leads.get(event.lead_article_id or -1),
            image=images.get(event.id),
        )
        for event in events
    ]

    article_rows = search_service.search_articles(q, limit=6)
    directory.load(row.Article.publisher_id for row in article_rows)
    article_items = [article_lite(row.Article, directory) for row in article_rows]

    publisher_rows = search_service.search_publishers(q, limit=5)
    publisher_items = [publisher_lite(row) for row in publisher_rows]

    suggestions = [item["title"] for item in event_items[:4]]
    took_ms = int((time.perf_counter() - started) * 1000)
    return SearchResultsOut(
        query=q,
        total=total + len(article_items) + len(publisher_items),
        took_ms=took_ms,
        events=event_items,
        articles=article_items,
        publishers=publisher_items,
        suggestions=suggestions,
    )


@router.get("/suggest", response_model=list[str])
def suggest(db: DbSession, q: str = Query(..., min_length=2, max_length=120)) -> list[str]:
    return SearchService(db).suggestions(q, limit=6)
