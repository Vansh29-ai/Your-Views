"""Event search with SQLite FTS5 (bm25 ranking) and a LIKE fallback.

The FTS table is maintained explicitly by the service layer (not by triggers) so that index
writes are testable and failures are visible. If FTS5 is unavailable in the local SQLite
build, keyword search degrades to ranked LIKE matching instead of breaking.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database.connection import engine
from app.database.models import Event, SearchDocument
from app.utils.text import content_tokens, truncate

logger = logging.getLogger(__name__)

_FTS_READY = False
_FTS_ENABLED = True


def ensure_fts() -> bool:
    global _FTS_READY, _FTS_ENABLED
    if _FTS_READY:
        return _FTS_ENABLED
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS event_fts USING fts5("
                    "event_id UNINDEXED, title, summary, keywords, publishers, "
                    "tokenize='porter unicode61')"
                )
            )
        _FTS_READY = True
        _FTS_ENABLED = True
    except Exception as exc:  # pragma: no cover - depends on sqlite build
        logger.warning("FTS5 unavailable, falling back to LIKE search: %s", exc)
        _FTS_READY = True
        _FTS_ENABLED = False
    return _FTS_ENABLED


def fts_available() -> bool:
    return ensure_fts()


def _fts_query(query: str) -> str:
    tokens = [re.sub(r'["*]', "", token) for token in content_tokens(query)][:8]
    tokens = [token for token in tokens if token]
    if not tokens:
        return ""
    return " AND ".join(f'"{token}"*' for token in tokens)


class SearchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ indexing
    def upsert_event(self, event: Event) -> None:
        document = self.db.get(SearchDocument, event.id)
        if document is None:
            document = SearchDocument(event_id=event.id)
            self.db.add(document)
        document.title = event.title or ""
        document.summary = event.summary or ""
        document.keywords = " ".join([*(event.keywords or []), *(event.entities or [])])
        document.publishers = " ".join(event.publishers or [])
        self.db.flush()

        if not ensure_fts():
            return
        try:
            self.db.execute(text("DELETE FROM event_fts WHERE event_id = :event_id"), {"event_id": event.id})
            self.db.execute(
                text(
                    "INSERT INTO event_fts (event_id, title, summary, keywords, publishers) "
                    "VALUES (:event_id, :title, :summary, :keywords, :publishers)"
                ),
                {
                    "event_id": event.id,
                    "title": document.title,
                    "summary": document.summary,
                    "keywords": document.keywords,
                    "publishers": document.publishers,
                },
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("FTS upsert failed for event %s: %s", event.id, exc)

    def delete_event(self, event_id: int) -> None:
        self.db.query(SearchDocument).filter(SearchDocument.event_id == event_id).delete()
        if ensure_fts():
            try:
                self.db.execute(text("DELETE FROM event_fts WHERE event_id = :event_id"), {"event_id": event_id})
            except Exception:  # pragma: no cover
                logger.debug("FTS delete failed for event %s", event_id, exc_info=True)

    def rebuild(self, events: list[Event] | None = None) -> int:
        if ensure_fts():
            self.db.execute(text("DELETE FROM event_fts"))
        self.db.query(SearchDocument).delete()
        self.db.flush()
        events = events if events is not None else list(self.db.scalars(select(Event)).all())
        for event in events:
            self.upsert_event(event)
        return len(events)

    # ------------------------------------------------------------------ querying
    def search_event_ids(self, query: str, *, limit: int = 40) -> list[tuple[int, float]]:
        query = (query or "").strip()
        if not query:
            return []
        if ensure_fts():
            match = _fts_query(query)
            if match:
                try:
                    rows = self.db.execute(
                        text(
                            "SELECT event_id, bm25(event_fts) AS rank FROM event_fts "
                            "WHERE event_fts MATCH :match ORDER BY rank LIMIT :limit"
                        ),
                        {"match": match, "limit": limit},
                    ).all()
                    if rows:
                        return [(int(row[0]), float(row[1])) for row in rows]
                except Exception as exc:  # pragma: no cover - bad query syntax etc.
                    logger.debug("FTS query failed (%s); using LIKE fallback", exc)
        return self._like_search(query, limit=limit)

    def _like_search(self, query: str, *, limit: int) -> list[tuple[int, float]]:
        pattern = f"%{query}%"
        events = self.db.scalars(
            select(Event)
            .where(
                Event.title.ilike(pattern)
                | Event.summary.ilike(pattern)
                | Event.category.ilike(pattern)
            )
            .order_by(Event.last_published_at.desc())
            .limit(limit * 3)
        ).all()
        lowered = query.lower()
        scored: list[tuple[int, float]] = []
        for event in events:
            score = 0.0
            if lowered in (event.title or "").lower():
                score += 2.0
            if lowered in (event.summary or "").lower():
                score += 1.0
            if lowered in " ".join(event.keywords or []):
                score += 0.8
            if lowered in " ".join(event.publishers or []):
                score += 0.5
            scored.append((event.id, -score))
        scored.sort(key=lambda item: item[1])
        return scored[:limit]

    def search_articles(self, query: str, *, limit: int = 20):
        from app.database.models import Article, Publisher

        tokens = content_tokens(query)[:6]
        if not tokens:
            return []
        conditions = []
        for token in tokens:
            pattern = f"%{token}%"
            conditions.append(Article.title.ilike(pattern) | Article.summary.ilike(pattern))
        statement = (
            select(Article, Publisher)
            .join(Publisher, Publisher.id == Article.publisher_id)
            .where(*conditions)
            .order_by(Article.published_at.desc())
            .limit(limit)
        )
        return self.db.execute(statement).all()

    def search_publishers(self, query: str, *, limit: int = 10):
        from app.database.models import Publisher

        pattern = f"%{query}%"
        return self.db.scalars(
            select(Publisher)
            .where(Publisher.name.ilike(pattern) | Publisher.short_name.ilike(pattern))
            .order_by(Publisher.name)
            .limit(limit)
        ).all()

    def suggestions(self, query: str, *, limit: int = 6) -> list[str]:
        results = self.search_event_ids(query, limit=limit)
        events = self.db.scalars(select(Event).where(Event.id.in_([r[0] for r in results]))).all() if results else []
        by_id = {event.id: event for event in events}
        return [truncate(by_id[event_id].title, 70) for event_id, _ in results if event_id in by_id]

    def build_document(self, event: Event) -> None:
        """Convenience wrapper used after event aggregate changes."""
        self.upsert_event(event)
