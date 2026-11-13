"""ORM → API serialisation helpers.

All datetime values are stored as naive UTC and exposed as ISO-8601 with an explicit ``Z`` so
the browser never has to guess the timezone.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Article, Event, Publisher
from app.utils.images import image_quality
from app.utils.text import truncate


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def publisher_lite(publisher: Publisher | None) -> dict:
    if publisher is None:
        return {
            "id": "unknown",
            "name": "Unknown",
            "short_name": "Unknown",
            "country": None,
            "tier": None,
            "accent": None,
            "access": "rss",
            "homepage": "",
        }
    return {
        "id": publisher.id,
        "name": publisher.name,
        "short_name": publisher.short_name,
        "country": publisher.country,
        "tier": publisher.tier,
        "accent": publisher.accent,
        "access": publisher.access,
        "homepage": publisher.homepage,
    }


class PublisherDirectory:
    """Request-scoped cache so event lists do not issue one query per publisher."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self._cache: dict[str, Publisher] = {}

    def get(self, publisher_id: str) -> Publisher | None:
        if publisher_id in self._cache:
            return self._cache[publisher_id]
        publisher = self.db.get(Publisher, publisher_id)
        if publisher is not None:
            self._cache[publisher_id] = publisher
        return publisher

    def load(self, publisher_ids: Iterable[str]) -> None:
        missing = [pid for pid in set(publisher_ids) if pid not in self._cache]
        if not missing:
            return
        for publisher in self.db.scalars(select(Publisher).where(Publisher.id.in_(missing))).all():
            self._cache[publisher.id] = publisher

    def lite(self, publisher_id: str) -> dict:
        return publisher_lite(self.get(publisher_id))


def _image_quality(url: str | None) -> int:
    """Publisher image CDNs differ wildly in rendition size. Prefer print-worthy sources."""
    return image_quality(url)


def best_image_article(articles: list[Article]) -> Article | None:
    candidates = [article for article in articles if article.image_url]
    if not candidates:
        return None
    return max(candidates, key=lambda article: (_image_quality(article.image_url), article.published_at))


def article_lite(article: Article, directory: PublisherDirectory) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "url": article.url,
        "published_at": iso(article.published_at),
        "category": article.category,
        "image_url": article.image_url,
        "publisher": directory.lite(article.publisher_id),
    }


def article_detail(article: Article, directory: PublisherDirectory, *, include_content: bool = True) -> dict:
    payload = article_lite(article, directory)
    payload.update(
        {
            "summary": article.summary or truncate(article.content, 320),
            "content": article.content if include_content else None,
            "author": article.author,
            "image_url": article.image_url,
            "entities": article.entities or [],
            "keywords": article.keywords or [],
            "word_count": article.word_count,
            "event_id": article.event_id,
            "event_code": f"EVT_{article.event_id:05d}" if article.event_id else None,
            "match_score": article.match_score,
            "match_method": article.match_method,
        }
    )
    return payload


def event_list_item(
    event: Event,
    directory: PublisherDirectory,
    *,
    lead_article: Article | None = None,
    image: tuple[str, str] | None = None,
) -> dict:
    publishers = event.publishers or []
    directory.load(publishers)
    if image is not None:
        image_url, image_credit = image
    else:
        image_url = lead_article.image_url if lead_article else None
        image_credit = directory.lite(lead_article.publisher_id)["name"] if image_url and lead_article else None
    return {
        "id": event.id,
        "code": event.code,
        "title": event.title,
        "summary": event.summary,
        "category": event.category,
        "article_count": event.article_count,
        "publisher_count": event.publisher_count,
        "publishers": [directory.lite(pid) for pid in publishers],
        "first_published_at": iso(event.first_published_at),
        "last_published_at": iso(event.last_published_at),
        "lead_article": article_lite(lead_article, directory) if lead_article else None,
        "image_url": image_url,
        "image_credit": image_credit,
        "keywords": event.keywords or [],
        "entities": event.entities or [],
        "categories": event.categories or [],
        "is_single_source": event.is_single_source,
    }


def event_detail(
    event: Event,
    articles: list[Article],
    directory: PublisherDirectory,
) -> dict:
    directory.load([article.publisher_id for article in articles])
    lead = next((a for a in articles if a.id == event.lead_article_id), articles[0] if articles else None)
    ordered = sorted(articles, key=lambda a: a.published_at)
    payload = event_list_item(event, directory, lead_article=lead)
    image_article = best_image_article(articles)
    if image_article is not None:
        payload["image_url"] = image_article.image_url
        payload["image_credit"] = directory.lite(image_article.publisher_id)["name"]
    payload["articles"] = [article_detail(article, directory) for article in ordered]
    payload["timeline"] = [
        {
            "article_id": article.id,
            "title": article.title,
            "published_at": iso(article.published_at),
            "publisher": directory.lite(article.publisher_id),
        }
        for article in ordered
    ]
    payload["emphasis"] = build_emphasis(articles, directory)
    span_hours = 0.0
    if ordered:
        span_hours = (ordered[-1].published_at - ordered[0].published_at).total_seconds() / 3600.0
    payload["stats"] = {
        "article_count": len(articles),
        "publisher_count": len({article.publisher_id for article in articles}),
        "span_hours": round(span_hours, 1),
        "first_published_at": iso(event.first_published_at),
        "last_published_at": iso(event.last_published_at),
    }
    return payload


def build_emphasis(articles: list[Article], directory: PublisherDirectory) -> dict:
    """Transparent, lexical emphasis comparison — never a bias or truth score.

    Entities are aggregated per publisher. "Shared" means mentioned by at least 60% of the
    publishers covering the event; "divergent" means mentioned by exactly one publisher.
    """
    from collections import Counter
    from math import ceil

    by_publisher: dict[str, list[Article]] = {}
    for article in articles:
        by_publisher.setdefault(article.publisher_id, []).append(article)

    publisher_entities: dict[str, dict[str, str]] = {}
    publisher_keywords: dict[str, Counter[str]] = {}
    entity_publishers: dict[str, set[str]] = {}
    display: dict[str, str] = {}

    for publisher_id, publisher_articles in by_publisher.items():
        entities: dict[str, str] = {}
        keywords: Counter[str] = Counter()
        for article in publisher_articles:
            for entity in article.entities or []:
                key = entity.lower().strip()
                if not key:
                    continue
                entities.setdefault(key, entity)
                entity_publishers.setdefault(key, set()).add(publisher_id)
                display.setdefault(key, entity)
            for keyword in article.keywords or []:
                keywords[keyword] += 1
        publisher_entities[publisher_id] = entities
        publisher_keywords[publisher_id] = keywords

    publisher_total = max(1, len(by_publisher))
    shared_threshold = 1 if publisher_total == 1 else ceil(publisher_total * 0.6)

    shared_keys = [
        key for key, publishers in entity_publishers.items()
        if len(publishers) >= shared_threshold
    ]
    divergent_keys = [
        key for key, publishers in entity_publishers.items()
        if len(publishers) == 1
    ]

    keyword_publishers: Counter[str] = Counter()
    for keywords in publisher_keywords.values():
        for keyword in keywords:
            keyword_publishers[keyword] += 1
    shared_keywords = [
        keyword for keyword, count in keyword_publishers.most_common()
        if count >= shared_threshold
    ][:12]

    rows: list[dict] = []
    for publisher_id, publisher_articles in by_publisher.items():
        latest = max(publisher_articles, key=lambda article: article.published_at)
        own = publisher_entities[publisher_id]
        unique = [
            own[key] for key in own
            if entity_publishers.get(key, set()) == {publisher_id}
        ]
        rows.append(
            {
                "publisher": directory.lite(publisher_id),
                "article_id": latest.id,
                "headline": latest.title,
                "published_at": iso(latest.published_at),
                "unique_entities": unique[:12],
                "shared_entities": [own[key] for key in shared_keys if key in own][:12],
                "keywords": [keyword for keyword, _ in publisher_keywords[publisher_id].most_common(10)],
                "word_count": sum(article.word_count for article in publisher_articles),
                "article_count": len(publisher_articles),
            }
        )

    rows.sort(key=lambda row: (-row["article_count"], row["publisher"]["name"]))

    return {
        "shared_entities": sorted(display[key] for key in shared_keys)[:20],
        "divergent_entities": sorted(display[key] for key in divergent_keys)[:24],
        "shared_keywords": shared_keywords,
        "publishers": rows,
        "method_note": (
            "Emphasis signals are lexical and entity based. “Shared” means mentioned by at least "
            "60% of the publishers covering this event. They describe what each publisher mentions; "
            "they are not bias scores, sentiment judgements, or claims about truth."
        ),
    }


def run_payload(run) -> dict:  # type: ignore[no-untyped-def]
    return {
        "id": run.id,
        "trigger": run.trigger,
        "status": run.status,
        "started_at": iso(run.started_at),
        "finished_at": iso(run.finished_at),
        "duration_ms": run.duration_ms,
        "feeds_total": run.feeds_total,
        "feeds_ok": run.feeds_ok,
        "feeds_failed": run.feeds_failed,
        "items_fetched": run.items_fetched,
        "items_new": run.items_new,
        "items_duplicate": run.items_duplicate,
        "items_invalid": run.items_invalid,
        "events_created": run.events_created,
        "events_updated": run.events_updated,
        "errors": run.errors or [],
    }
