#!/usr/bin/env python
"""Replay stored articles through the incremental matcher at different thresholds.

This does not touch the model or the network: it uses the embeddings already stored on each
article, rebuilds events inside a transaction, reports clustering statistics, then rolls back.
Use it to calibrate ``strong_similarity`` / ``weak_similarity`` before committing a change.

Usage (from backend/):
    ..\\.venv\\Scripts\\python.exe scripts\\simulate_matching.py --strong 0.70 --weak 0.58
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select  # noqa: E402

from app.config.settings import Settings  # noqa: E402
from app.database.connection import SessionLocal  # noqa: E402
from app.database.models import Article, Event  # noqa: E402
from app.ml.embeddings import unpack_vector  # noqa: E402
from app.ml.event_matcher import EventCandidate, choose_match  # noqa: E402
from app.services.event_service import EventService  # noqa: E402
from app.services.search_service import SearchService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strong", type=float, default=0.70)
    parser.add_argument("--weak", type=float, default=0.58)
    parser.add_argument("--window", type=int, default=96)
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument(
        "--commit", action="store_true", help="persist the rebuilt events instead of rolling back"
    )
    args = parser.parse_args()

    config = Settings(
        strong_similarity=args.strong,
        weak_similarity=args.weak,
        candidate_window_hours=args.window,
        enable_scheduler=False,
        ingest_on_startup=False,
    )

    with SessionLocal() as db:
        articles = list(
            db.scalars(
                select(Article)
                .where(Article.is_valid.is_(True), Article.embedding.is_not(None))
                .order_by(Article.published_at.asc())
                .limit(args.limit)
            ).all()
        )
        if not articles:
            print("No embedded articles found.")
            return

        try:
            before = int(db.scalar(select(func.count(Event.id))) or 0)
            search = SearchService(db)
            for event in db.scalars(select(Event)).all():
                search.delete_event(event.id)
                db.delete(event)
            for article in articles:
                article.event_id = None
                article.match_score = None
                article.match_method = None
            db.flush()

            service = EventService(db, config)
            created = 0
            for article in articles:
                vector = unpack_vector(article.embedding, article.embedding_dim)
                if vector is None:
                    continue
                candidates = []
                for event in service.candidate_events(article.published_at, article.embedding_model):
                    centroid = unpack_vector(event.centroid, event.centroid_dim)
                    if centroid is None:
                        continue
                    candidates.append(
                        EventCandidate(
                            event_id=event.id,
                            centroid=centroid,
                            entities={entity.lower() for entity in (event.entities or [])},
                            keywords={keyword.lower() for keyword in (event.keywords or [])},
                            last_published_at=event.last_published_at,
                        )
                    )
                decision = choose_match(
                    embedding=vector,
                    entities=article.entities or [],
                    keywords=article.keywords or [],
                    published_at=article.published_at,
                    candidates=candidates,
                    config=config,
                )
                if decision.matched and decision.event_id is not None:
                    event = db.get(Event, decision.event_id)
                    if event is not None:
                        service.assign_article(event, article, decision)
                        continue
                service.create_event_from_article(article)
                created += 1

            db.flush()
            events = list(db.scalars(select(Event)).all())
            multi = [event for event in events if event.publisher_count > 1]
            assigned = sum(event.article_count for event in events)
            multi_articles = sum(event.article_count for event in multi)
            print(f"thresholds strong={args.strong} weak={args.weak} window={args.window}h")
            print(f"articles={len(articles)} events_before={before} events_after={len(events)}")
            print(
                f"multi_source={len(multi)} ({len(multi) / max(1, len(events)):.0%}) "
                f"assigned={assigned} in_multi_source={multi_articles}"
            )
            print(f"avg_publishers={sum(e.publisher_count for e in events) / max(1, len(events)):.2f}")
            print("\nTop events:")
            for event in sorted(events, key=lambda item: (item.publisher_count, item.article_count), reverse=True)[:15]:
                print(
                    f"  [{event.publisher_count}p/{event.article_count}a] {event.title[:88]} "
                    f"({', '.join(event.publishers or [])})"
                )
        finally:
            if args.commit:
                db.commit()
                print("\nCommitted rebuilt events to the database.")
            else:
                db.rollback()
                print("\nTransaction rolled back; stored events are unchanged.")


if __name__ == "__main__":
    main()
