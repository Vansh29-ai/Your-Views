"""Centralised publisher/feed registry loaded from ``config/sources.json``.

The rest of the system never hardcodes a publisher: adding a source means adding a JSON
entry, and the collector, health checks and UI pick it up automatically.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import SOURCES_FILE
from app.database.models import Publisher

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedDefinition:
    id: str
    publisher_id: str
    url: str
    category: str | None = None
    timeout: float | None = None

    @property
    def display_category(self) -> str:
        return self.category or "World"


@dataclass(frozen=True)
class PublisherDefinition:
    id: str
    name: str
    short_name: str
    homepage: str
    country: str | None
    language: str
    tier: str | None
    accent: str | None
    access: str
    unavailable_reason: str | None
    feeds: tuple[FeedDefinition, ...] = field(default_factory=tuple)

    @property
    def rss_feeds(self) -> tuple[FeedDefinition, ...]:
        return tuple(feed for feed in self.feeds if feed.url)

    @property
    def available(self) -> bool:
        return bool(self.feeds) and self.access in {"rss", "api"}


class SourceManager:
    def __init__(self, path: Path | str = SOURCES_FILE) -> None:
        self.path = Path(path)
        self._publishers: dict[str, PublisherDefinition] = {}
        self._load_error: str | None = None
        self.load()

    def load(self) -> None:
        self._publishers = {}
        self._load_error = None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._load_error = f"Could not read source registry: {exc}"
            logger.error(self._load_error)
            return

        publishers: dict[str, PublisherDefinition] = {}
        for item in raw.get("publishers", []):
            try:
                publisher_id = str(item["id"]).strip()
                feeds = tuple(
                    FeedDefinition(
                        id=str(feed.get("id") or f"{publisher_id}-{index}"),
                        publisher_id=publisher_id,
                        url=str(feed.get("url", "")).strip(),
                        category=feed.get("category"),
                        timeout=feed.get("timeout"),
                    )
                    for index, feed in enumerate(item.get("feeds", []))
                    if feed.get("url")
                )
                publishers[publisher_id] = PublisherDefinition(
                    id=publisher_id,
                    name=str(item["name"]),
                    short_name=str(item.get("short_name") or item["name"]),
                    homepage=str(item.get("homepage") or ""),
                    country=item.get("country"),
                    language=str(item.get("language") or "en"),
                    tier=item.get("tier"),
                    accent=item.get("accent"),
                    access=str(item.get("access") or "rss"),
                    unavailable_reason=item.get("unavailable_reason"),
                    feeds=feeds,
                )
            except KeyError as exc:
                logger.warning("Skipping malformed publisher entry (%s): %s", exc, item)
        self._publishers = publishers
        logger.info("Loaded %s publishers / %s feeds", len(publishers), len(self.feeds))

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def publishers(self) -> list[PublisherDefinition]:
        return list(self._publishers.values())

    def get_publisher(self, publisher_id: str) -> PublisherDefinition | None:
        return self._publishers.get(publisher_id)

    @property
    def feeds(self) -> list[FeedDefinition]:
        return [feed for publisher in self._publishers.values() for feed in publisher.rss_feeds]

    def feeds_by_publisher(self) -> dict[str, list[FeedDefinition]]:
        return {publisher.id: list(publisher.rss_feeds) for publisher in self._publishers.values()}

    def publisher_names(self, publisher_id: str) -> list[str]:
        publisher = self._publishers.get(publisher_id)
        if not publisher:
            return []
        return list({publisher.name, publisher.short_name})

    def seed_publishers(self, db: Session) -> int:
        """Upsert publisher metadata so joins are always available in the API layer."""
        created = 0
        for definition in self._publishers.values():
            record = db.get(Publisher, definition.id)
            if record is None:
                record = Publisher(id=definition.id, name=definition.name, short_name=definition.short_name,
                                   homepage=definition.homepage)
                db.add(record)
                created += 1
            record.name = definition.name
            record.short_name = definition.short_name
            record.homepage = definition.homepage
            record.country = definition.country
            record.language = definition.language
            record.tier = definition.tier
            record.accent = definition.accent
            record.access = definition.access
            record.unavailable_reason = definition.unavailable_reason
            record.feed_count = len(definition.rss_feeds)
            record.enabled = definition.available
        db.flush()
        if created:
            logger.info("Seeded %s new publishers", created)
        return created

    def valid_publisher_ids(self) -> set[str]:
        return set(self._publishers)

    def publisher_map(self, db: Session) -> dict[str, Publisher]:
        return {publisher.id: publisher for publisher in db.scalars(select(Publisher)).all()}


source_manager = SourceManager()
