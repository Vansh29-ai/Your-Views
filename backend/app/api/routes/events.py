"""Event endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession, EventServiceDep
from app.api.schemas import EventDetailOut, EventListItem, PaginatedEvents
from app.api.serializers import PublisherDirectory, event_detail, event_list_item

router = APIRouter(prefix="/events", tags=["events"])

SortOption = Literal["latest", "coverage", "trending", "oldest", "relevance"]


@router.get("", response_model=PaginatedEvents)
def list_events(
    db: DbSession,
    service: EventServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    category: str | None = None,
    publisher: str | None = None,
    q: str | None = Query(None, max_length=160),
    sort: SortOption = "latest",
    min_publishers: int | None = Query(None, ge=1, le=20),
    window_hours: int | None = Query(None, ge=1, le=720),
    include_single: bool = True,
) -> PaginatedEvents:
    events, total = service.list_events(
        page=page,
        page_size=page_size,
        category=category,
        publisher=publisher,
        query=q,
        sort=sort,
        min_publishers=min_publishers,
        window_hours=window_hours,
        include_single=include_single,
    )
    directory = PublisherDirectory(db)
    leads = service.lead_articles(events)
    images = service.best_event_images(events)
    items = [
        event_list_item(
            event,
            directory,
            lead_article=leads.get(event.lead_article_id or -1),
            image=images.get(event.id),
        )
        for event in events
    ]
    pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedEvents(items=items, total=total, page=page, page_size=page_size, pages=pages, sort=sort)


@router.get("/{identifier}", response_model=EventDetailOut)
def get_event(identifier: str, db: DbSession, service: EventServiceDep) -> EventDetailOut:
    event = service.get_event(identifier)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    articles = service.get_event_articles(event.id)
    if not articles:
        raise HTTPException(status_code=404, detail="Event has no articles")
    directory = PublisherDirectory(db)
    return EventDetailOut(**event_detail(event, articles, directory))


@router.get("/{identifier}/similar", response_model=list[EventListItem])
def similar_events(
    identifier: str,
    db: DbSession,
    service: EventServiceDep,
    limit: int = Query(4, ge=1, le=12),
) -> list[EventListItem]:
    event = service.get_event(identifier)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    related = service.similar_events(event, limit=limit)
    directory = PublisherDirectory(db)
    leads = service.lead_articles(related)
    images = service.best_event_images(related)
    return [
        EventListItem(
            **event_list_item(
                item,
                directory,
                lead_article=leads.get(item.lead_article_id or -1),
                image=images.get(item.id),
            )
        )
        for item in related
    ]
