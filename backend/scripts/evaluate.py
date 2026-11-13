#!/usr/bin/env python
"""Offline quality report for the event index and the clustering configuration.

Usage (from backend/):
    ..\\.venv\\Scripts\\python.exe scripts\\evaluate.py --days 7
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import numpy as np  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.database.connection import SessionLocal  # noqa: E402
from app.database.models import Article, Event, utcnow  # noqa: E402
from app.ml.clustering import cluster_quality, cluster_vectors  # noqa: E402
from app.ml.embeddings import unpack_vector  # noqa: E402
from app.ml.similarity import cosine_matrix  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--eps", type=float, default=0.4)
    args = parser.parse_args()

    cutoff = utcnow() - timedelta(days=args.days)
    with SessionLocal() as db:
        articles = list(
            db.scalars(
                select(Article).where(Article.is_valid.is_(True), Article.published_at >= cutoff)
            ).all()
        )
        events = list(db.scalars(select(Event).where(Event.last_published_at >= cutoff)).all())

        usable = [
            (article, unpack_vector(article.embedding, article.embedding_dim))
            for article in articles
        ]
        usable = [(article, vector) for article, vector in usable if vector is not None]
        matrix = np.vstack([vector for _, vector in usable]) if usable else np.zeros((0, 0))

        result = None
        if len(usable) > 3:
            result = cluster_vectors(
                matrix,
                [article.published_at for article, _ in usable],
                eps=args.eps,
                min_samples=2,
                time_window_hours=72,
            )

        pair_sample = cosine_matrix(matrix)[np.triu_indices(len(matrix), k=1)] if len(matrix) > 1 else []
        multi = [event for event in events if event.publisher_count > 1]
        report = {
            "window_days": args.days,
            "articles": len(articles),
            "events": len(events),
            "multi_source_events": len(multi),
            "single_source_events": len(events) - len(multi),
            "avg_publishers_per_event": round(
                sum(event.publisher_count for event in events) / len(events), 2
            ) if events else 0,
            "publisher_coverage": dict(
                Counter(
                    publisher
                    for event in events
                    for publisher in (event.publishers or [])
                ).most_common()
            ),
            "pairwise_similarity": {
                "mean": round(float(np.mean(pair_sample)), 4) if len(pair_sample) else None,
                "p90": round(float(np.percentile(pair_sample, 90)), 4) if len(pair_sample) else None,
                "max": round(float(np.max(pair_sample)), 4) if len(pair_sample) else None,
            },
            "clustering_at_eps": args.eps,
            "batch_clusters": result.cluster_count if result else 0,
            "batch_quality": cluster_quality(matrix, result.labels) if result else {},
        }

        print(json.dumps(report, indent=2, default=str))

        print("\nLargest events:")
        for event in sorted(events, key=lambda item: item.publisher_count, reverse=True)[:12]:
            print(
                f"  [{event.publisher_count}p/{event.article_count}a] {event.title[:96]} "
                f"({', '.join(event.publishers or [])})"
            )


if __name__ == "__main__":
    main()
