"""Pydantic response models — the public API contract."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PublisherLite(ApiModel):
    id: str
    name: str
    short_name: str
    country: str | None = None
    tier: str | None = None
    accent: str | None = None
    access: str = "rss"
    homepage: str


class FeedHealthOut(ApiModel):
    feed_id: str
    url: str
    category: str | None = None
    status: str
    http_status: int | None = None
    latency_ms: int | None = None
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    consecutive_failures: int = 0
    error: str | None = None
    items_last_fetch: int = 0


class PublisherDetail(PublisherLite):
    feed_count: int = 0
    enabled: bool = True
    unavailable_reason: str | None = None
    article_count: int = 0
    event_count: int = 0
    last_published_at: datetime | None = None
    feeds: list[FeedHealthOut] = Field(default_factory=list)


class ArticleLite(ApiModel):
    id: int
    title: str
    url: str
    published_at: datetime
    category: str | None = None
    image_url: str | None = None
    publisher: PublisherLite


class ArticleOut(ArticleLite):
    summary: str | None = None
    content: str | None = None
    author: str | None = None
    image_url: str | None = None
    entities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    word_count: int = 0
    event_id: int | None = None
    event_code: str | None = None
    match_score: float | None = None
    match_method: str | None = None


class EventListItem(ApiModel):
    id: int
    code: str
    title: str
    summary: str | None = None
    category: str | None = None
    article_count: int
    publisher_count: int
    publishers: list[PublisherLite] = Field(default_factory=list)
    first_published_at: datetime
    last_published_at: datetime
    lead_article: ArticleLite | None = None
    image_url: str | None = None
    image_credit: str | None = None
    keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    is_single_source: bool = False


class TimelinePoint(ApiModel):
    article_id: int
    title: str
    published_at: datetime
    publisher: PublisherLite


class EmphasisPublisher(ApiModel):
    publisher: PublisherLite
    article_id: int
    headline: str
    published_at: datetime
    unique_entities: list[str] = Field(default_factory=list)
    shared_entities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    word_count: int = 0
    article_count: int = 1


class EmphasisOut(ApiModel):
    shared_entities: list[str] = Field(default_factory=list)
    divergent_entities: list[str] = Field(default_factory=list)
    shared_keywords: list[str] = Field(default_factory=list)
    publishers: list[EmphasisPublisher] = Field(default_factory=list)
    method_note: str = (
        "Emphasis signals are lexical and entity based. They describe what each publisher "
        "mentions, not which account is correct and not a bias score."
    )


class EventStatsOut(ApiModel):
    article_count: int
    publisher_count: int
    span_hours: float
    first_published_at: datetime
    last_published_at: datetime


class EventDetailOut(EventListItem):
    articles: list[ArticleOut] = Field(default_factory=list)
    timeline: list[TimelinePoint] = Field(default_factory=list)
    emphasis: EmphasisOut
    stats: EventStatsOut


class PaginatedEvents(ApiModel):
    items: list[EventListItem]
    total: int
    page: int
    page_size: int
    pages: int
    sort: str


class FacetValue(ApiModel):
    value: str
    label: str
    count: int


class FacetsOut(ApiModel):
    categories: list[FacetValue] = Field(default_factory=list)
    publishers: list[FacetValue] = Field(default_factory=list)


class SearchResultsOut(ApiModel):
    query: str
    total: int
    took_ms: int
    events: list[EventListItem] = Field(default_factory=list)
    articles: list[ArticleLite] = Field(default_factory=list)
    publishers: list[PublisherLite] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class RunOut(ApiModel):
    id: int
    trigger: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    feeds_total: int = 0
    feeds_ok: int = 0
    feeds_failed: int = 0
    items_fetched: int = 0
    items_new: int = 0
    items_duplicate: int = 0
    items_invalid: int = 0
    events_created: int = 0
    events_updated: int = 0
    errors: list[dict] = Field(default_factory=list)


class EmbedderOut(ApiModel):
    model: str
    dim: int
    semantic: bool
    backend: str


class StatsOverviewOut(ApiModel):
    events_total: int
    multi_source_events: int
    single_source_events: int
    articles_total: int
    publishers_total: int
    publishers_reporting: int
    events_last_24h: int
    articles_last_24h: int
    avg_publishers_per_event: float
    coverage_distribution: dict[str, int]
    categories: list[FacetValue]
    embedder: EmbedderOut
    latest_run: RunOut | None = None
    generated_at: datetime


class TimelineDayOut(ApiModel):
    date: str
    events: int
    articles: int


class HealthOut(ApiModel):
    status: Literal["ok", "degraded"]
    database: bool
    fts: bool
    embedder: EmbedderOut
    feeds_total: int
    feeds_healthy: int
    last_run_status: str | None = None
    version: str


class IngestStartOut(ApiModel):
    started: bool
    message: str
