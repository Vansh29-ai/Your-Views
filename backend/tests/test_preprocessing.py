"""Validation, normalisation and duplicate-detection tests."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.preprocessing.cleaner import clean_entry
from app.preprocessing.deduplicator import DuplicateDetector
from app.preprocessing.normalizer import normalize_category, parse_datetime
from app.preprocessing.validator import validate_article
from app.utils.text import canonicalize_url, sha256_hex, simhash_hex


def _entry(**overrides):
    entry = {
        "title": "Central bank raises interest rates for the third time this year",
        "summary": (
            "Policymakers voted to increase the benchmark rate by 25 basis points, citing persistent "
            "inflation and a tight labour market."
        ),
        "link": "https://example.com/business/rates?utm_source=rss",
        "links": [
            {
                "rel": "alternate",
                "href": "https://example.com/business/rates?utm_source=rss",
                "type": "text/html",
            }
        ],
        "published": "Thu, 13 Nov 2026 09:30:00 GMT",
        "_feed_category": "Business",
    }
    entry.update(overrides)
    return entry


def test_validate_article_accepts_realistic_entry():
    result = validate_article(
        title="Central bank raises interest rates for the third time this year",
        summary=(
            "Policymakers voted to increase the benchmark rate by 25 basis points, citing persistent "
            "inflation and a tight labour market."
        ),
        content="",
        url="https://example.com/business/rates",
        published_at=datetime.utcnow() - timedelta(hours=2),
    )
    assert result.ok


def test_validate_article_rejects_short_title_and_bad_url():
    short = validate_article(
        title="Markets up",
        summary="A" * 200,
        content="",
        url="https://example.com/a",
        published_at=datetime.utcnow(),
    )
    assert not short.ok and short.reason == "title_too_short"

    bad_url = validate_article(
        title="A properly long and informative headline about markets",
        summary="B" * 200,
        content="",
        url="ftp://example.com/a",
        published_at=datetime.utcnow(),
    )
    assert not bad_url.ok and bad_url.reason == "invalid_url"


def test_stale_and_future_articles_are_rejected():
    realistic_summary = (
        "Lawmakers debated the measure for several hours before the vote, with opposition parties "
        "raising objections about the projected deficit."
    )
    stale = validate_article(
        title="A properly long and informative headline about markets",
        summary=realistic_summary,
        content="",
        url="https://example.com/stale",
        published_at=datetime.utcnow() - timedelta(days=45),
    )
    assert stale.reason == "stale_article"

    future = validate_article(
        title="A properly long and informative headline about markets",
        summary=realistic_summary,
        content="",
        url="https://example.com/future",
        published_at=datetime.utcnow() + timedelta(days=2),
    )
    assert future.reason == "future_timestamp"


def test_parse_datetime_normalises_to_naive_utc():
    parsed = parse_datetime("Thu, 13 Nov 2026 09:30:00 +0530")
    assert parsed.tzinfo is None
    assert parsed.hour == 4


def test_normalize_category_maps_feed_taxonomy():
    assert normalize_category("Business") == "Business"
    assert normalize_category("world") == "World"
    assert normalize_category("Science and environment") == "Science"


def test_clean_entry_strips_tracking_and_publisher_suffix():
    draft, validation, _ = clean_entry(
        _entry(title="Markets rally as inflation cools — BBC News"),
        publisher_id="bbc",
        publisher_name="BBC News",
        publisher_names=["BBC News", "BBC"],
    )
    assert validation is None
    assert draft is not None
    assert draft.title == "Markets rally as inflation cools"
    assert "utm_source" not in draft.canonical_url
    assert draft.publisher_id == "bbc"
    assert draft.entities
    assert draft.keywords


def test_duplicate_detector_finds_url_content_and_simhash(db):
    from app.database.models import Article, Publisher

    db.add(Publisher(id="bbc", name="BBC News", short_name="BBC", homepage="https://bbc.co.uk"))
    db.flush()

    title = "Central bank raises interest rates for the third time this year"
    summary = "Policymakers voted to increase the benchmark rate by 25 basis points."
    url = "https://example.com/business/rates"
    canonical = canonicalize_url(url)
    article = Article(
        publisher_id="bbc",
        title=title,
        summary=summary,
        content=summary,
        url=url,
        canonical_url=canonical,
        url_hash=sha256_hex(canonical),
        content_hash=sha256_hex(f"{title}|{summary}"),
        simhash=simhash_hex(f"{title} {summary}"),
        published_at=datetime.utcnow(),
        category="Business",
        word_count=12,
    )
    db.add(article)
    db.commit()

    detector = DuplicateDetector(db)
    assert detector.reason_for(
        url_hash=sha256_hex(canonical),
        publisher_id="bbc",
        content_hash="unused",
        simhash_hex="0000000000000000",
    ) == "duplicate_url"
    assert detector.reason_for(
        url_hash=sha256_hex("https://example.com/other"),
        publisher_id="bbc",
        content_hash=sha256_hex(f"{title}|{summary}"),
        simhash_hex="0000000000000000",
    ) == "duplicate_content"
    assert detector.reason_for(
        url_hash=sha256_hex("https://example.com/third"),
        publisher_id="bbc",
        content_hash="different",
        simhash_hex=simhash_hex(f"{title} {summary}"),
    ) == "duplicate_simhash"
    # Same text at a different publisher is a perspective, not a duplicate.
    assert detector.reason_for(
        url_hash=sha256_hex("https://example.com/third"),
        publisher_id="cnn",
        content_hash=sha256_hex(f"{title}|{summary}"),
        simhash_hex=simhash_hex(f"{title} {summary}"),
    ) is None
