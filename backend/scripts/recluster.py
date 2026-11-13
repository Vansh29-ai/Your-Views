#!/usr/bin/env python
"""Rebuild events for a window of already-collected articles.

Usage (from backend/):
    ..\\.venv\\Scripts\\python.exe scripts\\recluster.py --days 7 --eps 0.4 --algorithm dbscan
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database.connection import SessionLocal  # noqa: E402
from app.database.init_db import init_db  # noqa: E402
from app.services.recluster_service import recluster  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-cluster stored articles into events")
    parser.add_argument("--days", type=int, default=7, help="window of event activity to rebuild")
    parser.add_argument("--eps", type=float, default=None, help="cosine distance threshold")
    parser.add_argument("--min-samples", type=int, default=None)
    parser.add_argument("--algorithm", choices=["dbscan", "agglomerative"], default="dbscan")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        summary = recluster(
            db,
            window_days=args.days,
            eps=args.eps,
            min_samples=args.min_samples,
            algorithm=args.algorithm,
        )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
