"""End-to-end ingestion test with mocked RSS feeds (no network)."""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy import select

from app.collectors.rss_collector import RSSCollector
from app.collectors.source_manager import FeedDefinition, PublisherDefinition, source_manager
from app.config.settings import Settings
from app.database.models import Article, Event, IngestionRun
from app.services.ingestion_service import IngestionService
from app.services.recluster_service import recluster

FEED_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>{title}</title>{items}</channel></rss>"""

ITEM_TEMPLATE = """
<item>
  <title>{title}</title>
  <link>{link}</link>
  <description>{description}</description>
  <pubDate>{published}</pubDate>
</item>
"""


def item(title: str, link: str, description: str, published: str) -> str:
    return ITEM_TEMPLATE.format(title=title, link=link, description=description, published=published)


ALPHA_FEED = FEED_TEMPLATE.format(
    title="Alpha",
    items="".join(
        [
            item(
                "Parliament approves national budget after marathon overnight debate",
                "https://alpha.test/news/budget",
                "Lawmakers passed the national budget with a narrow majority after an overnight session.",
                "Thu, 13 Nov 2026 08:00:00 GMT",
            ),
            item(
                "Parliament approves national budget after marathon overnight debate",
                "https://alpha.test/news/budget",
                "Duplicate URL that must be ignored.",
                "Thu, 13 Nov 2026 08:00:00 GMT",
            ),
            item(
                "Short",
                "https://alpha.test/news/short",
                "Too short to be useful.",
                "Thu, 13 Nov 2026 08:10:00 GMT",
            ),
        ]
    ),
)

BETA_FEED = FEED_TEMPLATE.format(
    title="Beta",
    items="".join(
        [
            item(
                "Parliament approves national budget following marathon overnight debate",
                "https://beta.test/politics/budget-vote",
                "The national budget passed after a marathon overnight debate in parliament.",
                "Thu, 13 Nov 2026 09:00:00 GMT",
            ),
            item(
                "Cricket team wins dramatic final in Mumbai",
                "https://beta.test/sport/final",
                "A late wicket sealed a dramatic two-run victory in the final in Mumbai.",
                "Thu, 13 Nov 2026 10:00:00 GMT",
            ),
        ]
    ),
)


def _publisher(identifier: str, name: str, feed_url: str, accent: str) -> PublisherDefinition:
    return PublisherDefinition(
        id=identifier,
        name=name,
        short_name=name,
        homepage=f"https://{identifier}.test",
        country="GB",
        language="en",
        tier="test",
        accent=accent,
        access="rss",
        unavailable_reason=None,
        feeds=(FeedDefinition(id=f"{identifier}-main", publisher_id=identifier, url=feed_url, category="World"),),
    )


def _handler(request: httpx.Request) -> httpx.Response:
    feeds = {
        "https://alpha.test/rss": ALPHA_FEED,
        "https://beta.test/rss": BETA_FEED,
    }
    body = feeds.get(str(request.url))
    if body is None:
        return httpx.Response(404)
    return httpx.Response(200, text=body, headers={"Content-Type": "application/rss+xml"})


@pytest.fixture()
def fake_sources(monkeypatch):
    publishers = {
        "alpha": _publisher("alpha", "Alpha News", "https://alpha.test/rss", "#FF0000"),
        "beta": _publisher("beta", "Beta Wire", "https://beta.test/rss", "#00AAFF"),
    }
    monkeypatch.setattr(source_manager, "_publishers", publishers)
    return publishers


async def test_full_ingestion_groups_cross_publisher_event(fake_sources, db):
    config = Settings(
        strong_similarity=0.30,
        weak_similarity=0.20,
        request_retries=0,
        candidate_window_hours=96,
    )
    collector = RSSCollector(client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)))
    service = IngestionService(config=config, collector_factory=lambda: collector)

    run_id = await service.run("test")
    db.expire_all()

    run = db.get(IngestionRun, run_id)
    assert run is not None
    assert run.status == "completed"
    assert run.items_fetched == 5
    assert run.items_new == 3
    assert run.items_duplicate == 1
    assert run.items_invalid == 1

    articles = db.scalars(select(Article)).all()
    assert len(articles) == 3
    assert all(article.event_id is not None for article in articles)
    assert all(article.embedding for article in articles)

    events = db.scalars(select(Event)).all()
    assert len(events) == 2
    multi = [event for event in events if event.publisher_count == 2]
    assert len(multi) == 1
    budget_event = multi[0]
    assert budget_event.article_count == 2
    assert set(budget_event.publishers) == {"alpha", "beta"}
    assert budget_event.code.startswith("EVT_")
    assert budget_event.centroid is not None

    # A second run must not duplicate anything (URL + content dedupe).
    second_run_id = await service.run("test")
    db.expire_all()
    second = db.get(IngestionRun, second_run_id)
    assert second is not None
    assert second.items_new == 0
    assert len(db.scalars(select(Article)).all()) == 3


async def test_recluster_rebuilds_events(fake_sources, db):
    config = Settings(strong_similarity=0.30, weak_similarity=0.20, request_retries=0)
    collector = RSSCollector(client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)))
    service = IngestionService(config=config, collector_factory=lambda: collector)
    await service.run("test")
    db.expire_all()

    before = len(db.scalars(select(Event)).all())
    summary = recluster(db, window_days=7, eps=0.5, min_samples=2, config=config)
    db.expire_all()

    assert summary["articles_processed"] == 3
    assert summary["events_created"] >= 1
    events = db.scalars(select(Event)).all()
    assert len(events) == summary["events_created"]
    assert before >= 1
    assert all(article.event_id is not None for article in db.scalars(select(Article)).all())
    assert all(event.publisher_count >= 1 for event in events)
