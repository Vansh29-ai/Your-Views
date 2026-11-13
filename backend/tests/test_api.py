"""API contract tests against a temporary SQLite database."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.database.models import Article
from app.ml.embeddings import embedding_service, pack_vector
from app.ml.event_matcher import MatchDecision
from app.services.event_service import EventService
from app.utils.text import canonicalize_url, sha256_hex, simhash_hex


def make_article(
    db,
    publisher_id: str,
    title: str,
    summary: str,
    url: str,
    published_at: datetime,
    image_url: str | None = None,
):
    vector = embedding_service.encode_one(f"{title} — {summary}")
    canonical = canonicalize_url(url)
    article = Article(
        publisher_id=publisher_id,
        title=title,
        summary=summary,
        content=summary,
        url=url,
        canonical_url=canonical,
        url_hash=sha256_hex(canonical),
        content_hash=sha256_hex(f"{title}|{summary}"),
        simhash=simhash_hex(f"{title} {summary}"),
        published_at=published_at,
        category="Business",
        language="en",
        image_url=image_url,
        entities=["Bank of England", "Andrew Bailey"],
        keywords=["interest", "rates", "inflation"],
        word_count=len(summary.split()),
        embedding=pack_vector(vector),
        embedding_dim=int(vector.shape[0]),
        embedding_model=embedding_service.info.model,
        is_valid=True,
    )
    db.add(article)
    db.flush()
    return article


def seed_two_publisher_event(db):
    now = datetime.utcnow()
    bbc = make_article(
        db,
        "bbc",
        "Bank of England raises interest rates to a fifteen-year high",
        "Policymakers voted to increase the benchmark rate by 25 basis points to tackle inflation.",
        "https://www.bbc.co.uk/news/business-1",
        now - timedelta(hours=3),
        image_url="https://ichef.bbci.co.uk/ace/standard/240/cpsprodpb/test.jpg",
    )
    cnn = make_article(
        db,
        "cnn",
        "UK central bank lifts interest rates as inflation persists",
        "The Bank of England raised borrowing costs again, citing persistent inflation.",
        "https://edition.cnn.com/business/2",
        now - timedelta(hours=2),
    )
    service = EventService(db)
    event = service.create_event_from_article(bbc)
    service.assign_article(
        event,
        cnn,
        MatchDecision(event_id=event.id, score=0.88, similarity=0.88, method="semantic"),
    )
    db.commit()
    return event


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["database"] is True
    assert payload["embedder"]["dim"] == 384


def test_event_list_and_detail(client, db):
    event = seed_two_publisher_event(db)

    listing = client.get("/api/events")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["publisher_count"] == 2
    assert item["code"] == event.code
    assert item["image_url"] == "https://ichef.bbci.co.uk/ace/standard/240/cpsprodpb/test.jpg"
    assert item["image_credit"] == "BBC News"
    assert {publisher["id"] for publisher in item["publishers"]} == {"bbc", "cnn"}

    detail = client.get(f"/api/events/{event.code}")
    assert detail.status_code == 200
    payload = detail.json()
    assert len(payload["articles"]) == 2
    assert payload["stats"]["publisher_count"] == 2
    assert payload["emphasis"]["publishers"]
    assert payload["timeline"][0]["published_at"] <= payload["timeline"][-1]["published_at"]

    missing = client.get("/api/events/EVT_99999")
    assert missing.status_code == 404


def test_event_filters_and_pagination(client, db):
    seed_two_publisher_event(db)
    filtered = client.get("/api/events", params={"min_publishers": 3})
    assert filtered.json()["total"] == 0

    category = client.get("/api/events", params={"category": "Business"})
    assert category.json()["total"] == 1

    publisher = client.get("/api/events", params={"publisher": "cnn"})
    assert publisher.json()["total"] == 1

    paged = client.get("/api/events", params={"page_size": 1, "page": 1})
    assert paged.json()["pages"] == 1


def test_search_returns_event_clusters(client, db):
    seed_two_publisher_event(db)
    response = client.get("/api/search", params={"q": "interest rates"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["events"]
    assert payload["events"][0]["publisher_count"] == 2

    empty = client.get("/api/search", params={"q": "zzzznotfound"})
    assert empty.status_code == 200
    assert empty.json()["events"] == []


def test_search_filters_apply_to_event_clusters(client, db):
    seed_two_publisher_event(db)

    matching = client.get("/api/search", params={"q": "interest", "category": "Business"})
    assert matching.status_code == 200
    assert len(matching.json()["events"]) == 1

    excluded = client.get("/api/search", params={"q": "interest", "category": "World"})
    assert excluded.status_code == 200
    assert excluded.json()["events"] == []

    publisher = client.get("/api/search", params={"q": "interest", "publisher": "cnn"})
    assert publisher.status_code == 200
    assert len(publisher.json()["events"]) == 1


def test_publishers_and_stats(client, db):
    seed_two_publisher_event(db)
    publishers = client.get("/api/publishers")
    assert publishers.status_code == 200
    by_id = {row["id"]: row for row in publishers.json()}
    assert by_id["bbc"]["article_count"] == 1
    assert by_id["reuters"]["enabled"] is False
    assert by_id["reuters"]["unavailable_reason"]

    overview = client.get("/api/stats/overview")
    assert overview.status_code == 200
    stats = overview.json()
    assert stats["events_total"] == 1
    assert stats["multi_source_events"] == 1
    assert stats["articles_total"] == 2
    assert stats["coverage_distribution"]["2"] == 1

    timeline = client.get("/api/stats/timeline", params={"days": 7})
    assert timeline.status_code == 200
    assert len(timeline.json()) == 7


def test_articles_endpoint(client, db):
    event = seed_two_publisher_event(db)
    response = client.get("/api/articles", params={"event_id": event.id})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    article_id = payload["items"][0]["id"]

    detail = client.get(f"/api/articles/{article_id}")
    assert detail.status_code == 200
    assert detail.json()["keywords"]
    assert detail.json()["event_code"] == event.code


def test_ingestion_status_endpoint(client):
    response = client.get("/api/admin/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["running"] is False
    assert payload["latest_run"] is None
    assert payload["publishers"] >= 12
