#!/usr/bin/env python
"""Re-extract entities/keywords from stored text and rebuild event aggregates + search index.

Safe to run repeatedly. Use after changing NER/keyword logic — it does not re-fetch or re-embed.

Usage (from backend/):
    ..\\.venv\\Scripts\\python.exe scripts\\reprocess_articles.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.database.connection import SessionLocal  # noqa: E402
from app.database.init_db import init_db  # noqa: E402
from app.database.models import Article, Event  # noqa: E402
from app.ml.entities import get_entity_extractor  # noqa: E402
from app.preprocessing.keywords import extract_keywords  # noqa: E402
from app.services.event_service import EventService  # noqa: E402
from app.services.search_service import SearchService  # noqa: E402


def main() -> None:
    init_db(sync_search=False)
    extractor = get_entity_extractor()
    with SessionLocal() as db:
        articles = list(db.scalars(select(Article)).all())
        for article in articles:
            article.entities = extractor.extract(f"{article.title}. {article.summary or ''}")
            article.keywords = extract_keywords(article.title, article.summary or "")
        db.flush()

        service = EventService(db)
        events = list(db.scalars(select(Event)).all())
        for event in events:
            members = service.get_event_articles(event.id)
            if members:
                service.recompute_aggregates(event, members)
        db.flush()

        search = SearchService(db)
        count = search.rebuild()
        db.commit()

    print(f"Reprocessed {len(articles)} articles, {len(events)} events, reindexed {count} events")
    print(f"NER backend: {extractor.method}")


if __name__ == "__main__":
    main()
