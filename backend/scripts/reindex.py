#!/usr/bin/env python
"""Rebuild the FTS index and search documents from stored events.

Usage (from backend/):
    ..\\.venv\\Scripts\\python.exe scripts\\reindex.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database.connection import SessionLocal  # noqa: E402
from app.database.init_db import init_db  # noqa: E402
from app.services.search_service import SearchService  # noqa: E402


def main() -> None:
    init_db(sync_search=False)
    with SessionLocal() as db:
        count = SearchService(db).rebuild()
        db.commit()
    print(f"Reindexed {count} events")


if __name__ == "__main__":
    main()
