"""Event lifecycle: creation, incremental assignment, aggregates and event feeds."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config.settings import Settings, settings
from app.database.models import Article, Event, Publisher, utcnow
from app.ml.embeddings import pack_vector, unpack_vector
from app.ml.event_matcher import MatchDecision
from app.ml.similarity import centroid as compute_centroid
from app.services.search_service import SearchService
from app.utils.images import choose_best_image
from app.utils.text import truncate

logger = logging.getLogger(__name__)

MAX_EVENT_ENTITIES = 24
MAX_EVENT_KEYWORDS = 18


def event_code(event_id: int) -> str:
    return f"EVT_{event_id:05d}"


class EventService:
    def __init__(self, db: Session, config: Settings | None = None) -> None:
        self.db = db
        self.config = config or settings
        self.search = SearchService(db)

    # ------------------------------------------------------------------ creation
    def create_event_from_article(self, article: Article) -> Event:
        now = utcnow()
        event = Event(
            code="pending",
            title=truncate(article.title, self.config.event_title_max_chars, ""),
            summary=truncate(article.summary or article.content, self.config.event_summary_max_chars),
            category=article.category,
            lead_article_id=article.id,
            lead_publisher_id=article.publisher_id,
            article_count=1,
            publisher_count=1,
            publishers=[article.publisher_id],
            keywords=list(article.keywords or [])[:MAX_EVENT_KEYWORDS],
            entities=list(article.entities or [])[:MAX_EVENT_ENTITIES],
            categories=[article.category] if article.category else [],
            centroid=article.embedding,
            centroid_dim=article.embedding_dim,
            embedding_model=article.embedding_model,
            first_published_at=article.published_at,
            last_published_at=article.published_at,
            created_at=now,
            updated_at=now,
        )
        self.db.add(event)
        self.db.flush()
        event.code = event_code(event.id)
        article.event_id = event.id
        article.match_method = article.match_method or "new_event"
        self.db.flush()
        self.search.upsert_event(event)
        return event

    def assign_article(self, event: Event, article: Article, decision: MatchDecision) -> None:
        article.event_id = event.id
        article.match_score = round(decision.score, 4)
        article.match_method = decision.method
        self._update_aggregate(event, article, decision)
        self.db.flush()
        self.search.upsert_event(event)

    # ------------------------------------------------------------------ aggregates
    def _update_aggregate(self, event: Event, article: Article, decision: MatchDecision) -> None:
        previous_count = max(event.article_count or 0, 1)
        previous_first = event.first_published_at
        vector = unpack_vector(article.embedding, article.embedding_dim)
        stored = unpack_vector(event.centroid, event.centroid_dim)
        if vector is not None:
            if stored is not None and stored.shape == vector.shape:
                blended = (stored * previous_count + vector) / (previous_count + 1)
                norm = float(np.linalg.norm(blended))
                event.centroid = pack_vector(blended / norm if norm > 0 else blended)
            else:
                event.centroid = pack_vector(vector)
            event.centroid_dim = int(vector.shape[0])
            event.embedding_model = article.embedding_model

        publishers = list(dict.fromkeys([*(event.publishers or []), article.publisher_id]))
        event.publishers = publishers
        event.publisher_count = len(publishers)

        categories = list(dict.fromkeys([*(event.categories or []), *([article.category] if article.category else [])]))
        event.categories = categories
        if not event.category and article.category:
            event.category = article.category

        event.entities = self._merge_unique(event.entities or [], article.entities or [], MAX_EVENT_ENTITIES)
        event.keywords = self._merge_unique(event.keywords or [], article.keywords or [], MAX_EVENT_KEYWORDS)

        event.first_published_at = min(previous_first or article.published_at, article.published_at)
        event.last_published_at = max(event.last_published_at, article.published_at)
        event.updated_at = utcnow()
        event.article_count = (event.article_count or 0) + 1

        # Representative headline = earliest coverage of the event.
        if event.lead_article_id is None or previous_first is None or article.published_at < previous_first:
            event.lead_article_id = article.id
            event.lead_publisher_id = article.publisher_id
            event.title = truncate(article.title, self.config.event_title_max_chars, "")
            event.summary = truncate(
                article.summary or article.content, self.config.event_summary_max_chars
            )

    @staticmethod
    def _merge_unique(existing: list[str], incoming: list[str], limit: int) -> list[str]:
        merged = list(dict.fromkeys([*(existing or []), *(incoming or [])]))
        return merged[:limit]

    def recompute_aggregates(self, event: Event, articles: list[Article]) -> None:
        """Full recomputation from member articles (used after batch re-clustering)."""
        embedded = [
            (article, unpack_vector(article.embedding, article.embedding_dim))
            for article in articles
        ]
        embedded = [(article, vector) for article, vector in embedded if vector is not None]
        if embedded:
            matrix = np.vstack([vector for _, vector in embedded])
            centre = compute_centroid(matrix)
            event.centroid = pack_vector(centre)
            event.centroid_dim = int(centre.shape[0])
            event.embedding_model = embedded[0][0].embedding_model
        else:
            event.centroid = None
            event.centroid_dim = None
            event.embedding_model = None

        ordered = sorted(articles, key=lambda a: a.published_at)
        event.article_count = len(articles)
        event.publishers = list(dict.fromkeys(a.publisher_id for a in articles))
        event.publisher_count = len(event.publishers)
        event.categories = list(dict.fromkeys(a.category for a in articles if a.category))
        event.category = event.categories[0] if event.categories else event.category
        event.first_published_at = ordered[0].published_at if ordered else event.first_published_at
        event.last_published_at = ordered[-1].published_at if ordered else event.last_published_at
        if ordered:
            lead = ordered[0]
            event.lead_article_id = lead.id
            event.lead_publisher_id = lead.publisher_id
            event.title = truncate(lead.title, self.config.event_title_max_chars, "")
            event.summary = truncate(
                lead.summary or lead.content, self.config.event_summary_max_chars
            )
        entities: list[str] = []
        keywords: list[str] = []
        for article in ordered:
            entities = self._merge_unique(entities, article.entities or [], MAX_EVENT_ENTITIES)
            keywords = self._merge_unique(keywords, article.keywords or [], MAX_EVENT_KEYWORDS)
        event.entities = entities
        event.keywords = keywords
        event.updated_at = utcnow()
        self.search.upsert_event(event)

    # ------------------------------------------------------------------ queries
    def get_event(self, identifier: str | int) -> Event | None:
        statement = select(Event).options(selectinload(Event.articles).selectinload(Article.publisher))
        if isinstance(identifier, int) or str(identifier).isdigit():
            return self.db.scalar(statement.where(Event.id == int(identifier)))
        return self.db.scalar(statement.where(Event.code == str(identifier).upper()))

    def get_event_articles(self, event_id: int) -> list[Article]:
        return list(
            self.db.scalars(
                select(Article)
                .options(selectinload(Article.publisher))
                .where(Article.event_id == event_id, Article.is_valid.is_(True))
                .order_by(Article.published_at.desc())
            ).all()
        )

    def candidate_events(self, published_at: datetime, embedding_model: str | None = None) -> list[Event]:
        """Recent events expressed in the *same* vector space as the incoming article."""
        cutoff = published_at - timedelta(hours=self.config.candidate_window_hours)
        statement = (
            select(Event)
            .where(Event.last_published_at >= cutoff)
            .order_by(Event.last_published_at.desc())
            .limit(self.config.candidate_limit)
        )
        if embedding_model:
            statement = statement.where(Event.embedding_model == embedding_model)
        return list(self.db.scalars(statement).all())

    def purge_empty_events(self) -> int:
        empty = self.db.scalars(select(Event).where(Event.article_count <= 0)).all()
        for event in empty:
            self.search.delete_event(event.id)
            self.db.delete(event)
        return len(empty)

    def category_counts(self) -> list[tuple[str, int]]:
        rows = self.db.execute(
            select(Event.category, func.count(Event.id))
            .where(Event.category.is_not(None))
            .group_by(Event.category)
            .order_by(func.count(Event.id).desc())
        ).all()
        return [(str(row[0]), int(row[1])) for row in rows if row[0]]

    # ------------------------------------------------------------------ listing
    def list_events(
        self,
        *,
        page: int = 1,
        page_size: int = 12,
        category: str | None = None,
        publisher: str | None = None,
        query: str | None = None,
        sort: str = "latest",
        min_publishers: int | None = None,
        window_hours: int | None = None,
        include_single: bool = True,
    ) -> tuple[list[Event], int]:
        from sqlalchemy import String, case, cast

        statement = select(Event)
        conditions = []

        if category:
            conditions.append(Event.category == category)
        if publisher:
            conditions.append(cast(Event.publishers, String).like(f'%"{publisher}"%'))
        if min_publishers is not None:
            conditions.append(Event.publisher_count >= min_publishers)
        elif not include_single:
            conditions.append(Event.publisher_count >= 2)
        if window_hours:
            cutoff = utcnow() - timedelta(hours=window_hours)
            conditions.append(Event.last_published_at >= cutoff)

        relevance_order: dict[int, int] = {}
        if query:
            from app.services.search_service import SearchService

            results = SearchService(self.db).search_event_ids(query, limit=200)
            if not results:
                return [], 0
            ids = [event_id for event_id, _ in results]
            relevance_order = {event_id: index for index, event_id in enumerate(ids)}
            conditions.append(Event.id.in_(ids))

        if conditions:
            statement = statement.where(*conditions)

        total = int(
            self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )

        if query and sort == "relevance":
            ordering = case(relevance_order, value=Event.id, else_=len(relevance_order))
            statement = statement.order_by(ordering)
        elif sort == "coverage":
            statement = statement.order_by(
                Event.publisher_count.desc(), Event.article_count.desc(), Event.last_published_at.desc()
            )
        elif sort == "trending":
            statement = statement.order_by(
                (Event.publisher_count * 3 + Event.article_count).desc(),
                Event.publisher_count.desc(),
                Event.last_published_at.desc(),
            )
        elif sort == "oldest":
            statement = statement.order_by(Event.first_published_at.asc())
        else:
            statement = statement.order_by(Event.last_published_at.desc())

        statement = statement.offset(max(0, (page - 1) * page_size)).limit(page_size)
        events = list(self.db.scalars(statement).all())
        return events, total

    def lead_articles(self, events: list[Event]) -> dict[int, Article]:
        lead_ids = [event.lead_article_id for event in events if event.lead_article_id]
        if not lead_ids:
            return {}
        rows = self.db.scalars(select(Article).where(Article.id.in_(lead_ids))).all()
        return {article.id: article for article in rows}

    def best_event_images(self, events: list[Event]) -> dict[int, tuple[str, str]]:
        """Choose the most print-worthy provided image per event in a single query."""
        event_ids = [event.id for event in events]
        if not event_ids:
            return {}
        rows = self.db.execute(
            select(Article.event_id, Article.image_url, Publisher.name, Article.published_at)
            .join(Publisher, Publisher.id == Article.publisher_id)
            .where(
                Article.event_id.in_(event_ids),
                Article.image_url.is_not(None),
                Article.image_url != "",
            )
        ).all()
        return choose_best_image(
            [(int(row[0]), str(row[1]), str(row[2]), row[3]) for row in rows if row[0] is not None]
        )

    def similar_events(self, event: Event, *, limit: int = 4) -> list[Event]:
        """Nearest events by centroid cosine, excluding the event itself."""
        vector = unpack_vector(event.centroid, event.centroid_dim)
        if vector is None:
            return []
        candidates = self.db.scalars(
            select(Event)
            .where(
                Event.id != event.id,
                Event.embedding_model == event.embedding_model,
                Event.last_published_at >= event.last_published_at - timedelta(days=7),
            )
            .order_by(Event.last_published_at.desc())
            .limit(120)
        ).all()
        scored: list[tuple[float, Event]] = []
        for candidate in candidates:
            other = unpack_vector(candidate.centroid, candidate.centroid_dim)
            if other is None or other.shape != vector.shape:
                continue
            scored.append((float(np.dot(vector, other)), candidate))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [candidate for _, candidate in scored[:limit]]

    def publisher_counts(self) -> list[tuple[str, int]]:

        rows = self.db.execute(
            select(Event.publishers, func.count(Event.id)).group_by(Event.publishers)
        ).all()
        counts: dict[str, int] = {}
        for publishers, count in rows:
            for publisher_id in publishers or []:
                counts[publisher_id] = counts.get(publisher_id, 0) + int(count)
        return sorted(counts.items(), key=lambda item: -item[1])
