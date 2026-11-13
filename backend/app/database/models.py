"""SQLAlchemy models for YOUR VIEWS.

Storage is deliberately relational (publisher → article → event) so that an event is a
first-class object rather than a computed view over a flat article list. Embeddings are
stored as packed float32 blobs next to the model name that produced them, which makes
re-embedding migrations explicit and prevents mixing vector spaces.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite friendly, serialised with a trailing Z)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Publisher(Base):
    __tablename__ = "publishers"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    short_name: Mapped[str] = mapped_column(String(60), nullable=False)
    homepage: Mapped[str] = mapped_column(String(400), nullable=False)
    country: Mapped[str | None] = mapped_column(String(8))
    language: Mapped[str] = mapped_column(String(8), default="en")
    tier: Mapped[str | None] = mapped_column(String(40))
    accent: Mapped[str | None] = mapped_column(String(16))
    access: Mapped[str] = mapped_column(String(32), default="rss")
    unavailable_reason: Mapped[str | None] = mapped_column(Text)
    feed_count: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    articles: Mapped[list["Article"]] = relationship(back_populates="publisher")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(60), index=True)
    # Representative (lead) article and its publisher.
    lead_article_id: Mapped[int | None] = mapped_column(Integer)
    lead_publisher_id: Mapped[str | None] = mapped_column(String(40))

    article_count: Mapped[int] = mapped_column(Integer, default=0)
    publisher_count: Mapped[int] = mapped_column(Integer, default=0)
    publishers: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    entities: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Simple, transparent attention signal: how many distinct categories feeds covered it.
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)

    centroid: Mapped[bytes | None] = mapped_column()
    centroid_dim: Mapped[int | None] = mapped_column(Integer)
    embedding_model: Mapped[str | None] = mapped_column(String(200))

    first_published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    articles: Mapped[list["Article"]] = relationship(
        back_populates="event", order_by="Article.published_at.desc()"
    )

    __table_args__ = (
        Index("ix_events_last_pub_desc", last_published_at.desc()),
        Index("ix_events_publisher_count", publisher_count.desc()),
    )

    @property
    def is_single_source(self) -> bool:
        return (self.publisher_count or 0) <= 1


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    publisher_id: Mapped[str] = mapped_column(ForeignKey("publishers.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    simhash: Mapped[str | None] = mapped_column(String(32))
    author: Mapped[str | None] = mapped_column(String(200))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    category: Mapped[str | None] = mapped_column(String(60), index=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    entities: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    embedding: Mapped[bytes | None] = mapped_column()
    embedding_dim: Mapped[int | None] = mapped_column(Integer)
    embedding_model: Mapped[str | None] = mapped_column(String(200))
    embedding_hash: Mapped[str | None] = mapped_column(String(64))

    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), index=True
    )
    match_score: Mapped[float | None] = mapped_column(Float)
    match_method: Mapped[str | None] = mapped_column(String(40))

    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    invalid_reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    publisher: Mapped[Publisher] = relationship(back_populates="articles")
    event: Mapped[Event | None] = relationship(back_populates="articles")

    __table_args__ = (
        UniqueConstraint("url_hash", name="uq_articles_url_hash"),
        Index("ix_articles_publisher_event", "publisher_id", "event_id"),
        Index("ix_articles_event_published", "event_id", "published_at"),
    )


class FeedHealth(Base):
    __tablename__ = "feed_health"

    feed_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    publisher_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    category: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(24), default="unknown")
    http_status: Mapped[int | None] = mapped_column(Integer)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime)
    items_last_fetch: Mapped[int] = mapped_column(Integer, default=0)
    total_items_fetched: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    etag: Mapped[str | None] = mapped_column(String(300))
    last_modified: Mapped[str | None] = mapped_column(String(120))


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trigger: Mapped[str] = mapped_column(String(40), default="manual")
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    feeds_total: Mapped[int] = mapped_column(Integer, default=0)
    feeds_ok: Mapped[int] = mapped_column(Integer, default=0)
    feeds_failed: Mapped[int] = mapped_column(Integer, default=0)
    items_fetched: Mapped[int] = mapped_column(Integer, default=0)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    items_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    items_invalid: Mapped[int] = mapped_column(Integer, default=0)
    events_created: Mapped[int] = mapped_column(Integer, default=0)
    events_updated: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[dict]] = mapped_column(JSON, default=list)


class SearchDocument(Base):
    """Mirror of searchable event text used to keep SQLite FTS in sync explicitly."""

    __tablename__ = "search_documents"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    publishers: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
