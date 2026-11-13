"""Batch re-clustering over a window of stored articles.

This is the offline counterpart to incremental matching. It is destructive by design: events
inside the window are rebuilt from scratch using DBSCAN over stored embeddings plus the same
time-window constraint. Run it after tuning thresholds, or to repair drift.

Event codes are re-issued during a rebuild; article URLs and content are unaffected.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config.settings import Settings, settings
from app.database.models import Article, Event, utcnow
from app.ml.clustering import cluster_quality, cluster_vectors
from app.ml.embeddings import unpack_vector
from app.ml.event_matcher import MatchDecision
from app.services.event_service import EventService
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


def recluster(
    db: Session,
    *,
    window_days: int = 7,
    eps: float | None = None,
    min_samples: int | None = None,
    algorithm: str = "dbscan",
    config: Settings | None = None,
) -> dict:
    config = config or settings
    eps = config.cluster_eps if eps is None else eps
    min_samples = config.cluster_min_samples if min_samples is None else min_samples
    cutoff = utcnow() - timedelta(days=window_days)

    scoped_event_ids = list(
        db.scalars(select(Event.id).where(Event.last_published_at >= cutoff)).all()
    )
    articles = list(
        db.scalars(
            select(Article).where(
                Article.is_valid.is_(True),
                or_(Article.event_id.is_(None), Article.event_id.in_(scoped_event_ids or [-1])),
            )
        ).all()
    )

    search = SearchService(db)
    for event_id in scoped_event_ids:
        search.delete_event(event_id)
    for event_id in scoped_event_ids:
        event = db.get(Event, event_id)
        if event is not None:
            db.delete(event)
    for article in articles:
        article.event_id = None
        article.match_score = None
        article.match_method = None
    db.flush()

    embedded = [article for article in articles if article.embedding is not None]
    vectors = [unpack_vector(article.embedding, article.embedding_dim) for article in embedded]
    usable = [(article, vector) for article, vector in zip(embedded, vectors) if vector is not None]

    service = EventService(db, config)
    events_created = 0
    clustered_articles = 0
    quality: dict[str, float] = {}

    if usable:
        import numpy as np

        matrix = np.vstack([vector for _, vector in usable])
        timestamps = [article.published_at for article, _ in usable]
        result = cluster_vectors(
            matrix,
            timestamps,
            eps=eps,
            min_samples=min_samples,
            time_window_hours=config.cluster_time_window_hours,
            algorithm=algorithm,
        )
        quality = cluster_quality(matrix, result.labels)
        for group in sorted(result.clusters(), key=lambda g: min(timestamps[i] for i in g)):
            members = sorted((usable[i][0] for i in group), key=lambda a: a.published_at)
            if not members:
                continue
            event = service.create_event_from_article(members[0])
            for other in members[1:]:
                service.assign_article(
                    event,
                    other,
                    MatchDecision(
                        event_id=event.id,
                        score=1.0,
                        similarity=1.0,
                        method="batch_cluster",
                        reason="batch_clustering",
                    ),
                )
            service.recompute_aggregates(event, members)
            events_created += 1
            clustered_articles += len(members)

    # Articles without a cluster become single-source events (visible, but clearly labelled).
    clustered_ids = {
        article.id for article in articles if article.event_id is not None
    }
    for article in articles:
        if article.id in clustered_ids:
            continue
        event = service.create_event_from_article(article)
        service.recompute_aggregates(event, [article])
        events_created += 1

    purged = service.purge_empty_events()
    search.rebuild()
    db.commit()

    summary = {
        "window_days": window_days,
        "articles_processed": len(articles),
        "articles_clustered": clustered_articles,
        "events_created": events_created,
        "empty_events_purged": purged,
        "algorithm": algorithm,
        "eps": eps,
        "min_samples": min_samples,
        "quality": quality,
    }
    logger.info("Recluster complete: %s", summary)
    return summary
