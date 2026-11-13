"""Database bootstrap: tables, publisher registry, search index consistency."""

from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.collectors.source_manager import source_manager
from app.database.connection import Base, SessionLocal, engine
from app.database.models import Event, SearchDocument
from app.services.search_service import SearchService, ensure_fts

logger = logging.getLogger(__name__)


def init_db(*, sync_search: bool = True) -> None:
    Base.metadata.create_all(bind=engine)
    ensure_fts()
    with SessionLocal() as db:
        source_manager.seed_publishers(db)
        db.commit()
        if sync_search:
            event_count = int(db.scalar(select(func.count(Event.id))) or 0)
            doc_count = int(db.scalar(select(func.count(SearchDocument.event_id))) or 0)
            if event_count and doc_count != event_count:
                logger.info("Rebuilding search index (%s events, %s documents)", event_count, doc_count)
                SearchService(db).rebuild()
                db.commit()
