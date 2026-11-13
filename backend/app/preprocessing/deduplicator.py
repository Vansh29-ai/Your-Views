"""Duplicate detection.

Three layers:
1. Canonical URL match (global) — the same page must never be ingested twice.
2. Exact content fingerprint match *within a publisher* — republished wire copy.
3. 64-bit SimHash near-duplicate match *within a publisher* — rewritten internal duplicates.

Deliberately, near-duplicate text from *different* publishers is kept. That is not a
duplicate; it is the multi-perspective signal the product exists to show.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Article, utcnow
from app.utils.text import hamming_distance

NEAR_DUPLICATE_MAX_DISTANCE = 3
SIMHASH_LOOKBACK_DAYS = 14


class DuplicateDetector:
    def __init__(self, db: Session) -> None:
        self.db = db

    def reason_for(self, *, url_hash: str, publisher_id: str, content_hash: str, simhash_hex: str) -> str | None:
        if self.url_exists(url_hash):
            return "duplicate_url"
        if self._publisher_content_exists(publisher_id, content_hash):
            return "duplicate_content"
        if self._publisher_near_duplicate(publisher_id, simhash_hex):
            return "duplicate_simhash"
        return None

    def url_exists(self, url_hash: str) -> bool:
        if not url_hash:
            return False
        return (
            self.db.scalar(select(Article.id).where(Article.url_hash == url_hash).limit(1))
            is not None
        )

    def _publisher_content_exists(self, publisher_id: str, content_hash: str) -> bool:
        cutoff = utcnow() - timedelta(days=45)
        return (
            self.db.scalar(
                select(Article.id)
                .where(
                    Article.publisher_id == publisher_id,
                    Article.content_hash == content_hash,
                    Article.published_at >= cutoff,
                )
                .limit(1)
            )
            is not None
        )

    def _publisher_near_duplicate(self, publisher_id: str, simhash_hex: str) -> bool:
        if not simhash_hex:
            return False
        try:
            target = int(simhash_hex, 16)
        except ValueError:
            return False
        cutoff = utcnow() - timedelta(days=SIMHASH_LOOKBACK_DAYS)
        rows = self.db.execute(
            select(Article.simhash)
            .where(
                Article.publisher_id == publisher_id,
                Article.published_at >= cutoff,
                Article.simhash.is_not(None),
            )
            .order_by(Article.published_at.desc())
            .limit(400)
        ).scalars()
        for candidate in rows:
            try:
                if hamming_distance(target, int(candidate, 16)) <= NEAR_DUPLICATE_MAX_DISTANCE:
                    return True
            except (TypeError, ValueError):
                continue
        return False
