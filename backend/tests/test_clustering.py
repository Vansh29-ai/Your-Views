"""Batch clustering tests (DBSCAN + agglomerative + time-window splitting)."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from app.ml.clustering import cluster_quality, cluster_vectors


def _cluster(seed: int, size: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = np.zeros(384, dtype=np.float32)
    base[seed % 10] = 1.0
    vectors = base + rng.normal(0, 0.012, size=(size, 384)).astype(np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def _timestamps(count: int, *, spacing_hours: float = 1.0) -> list[datetime]:
    start = datetime(2026, 11, 10, 8, 0, 0)
    return [start + timedelta(hours=index * spacing_hours) for index in range(count)]


def test_dbscan_finds_two_clusters_and_noise():
    vectors = np.vstack([_cluster(1, 4), _cluster(6, 4), _cluster(9, 1)])
    result = cluster_vectors(
        vectors, _timestamps(len(vectors)), eps=0.15, min_samples=2, time_window_hours=72
    )
    assert result.cluster_count == 2
    assert len(result.clusters()) == 2
    assert result.labels[-1] == -1


def test_time_gap_splits_a_semantic_cluster():
    vectors = _cluster(2, 4)
    timestamps = [datetime(2026, 11, 1, 9, 0) + timedelta(days=index * 6) for index in range(4)]
    result = cluster_vectors(
        vectors, timestamps, eps=0.2, min_samples=2, time_window_hours=72
    )
    assert result.cluster_count == 0


def test_agglomerative_matches_dbscan_partition():
    vectors = np.vstack([_cluster(3, 3), _cluster(8, 3)])
    timestamps = _timestamps(len(vectors))
    dbscan = cluster_vectors(vectors, timestamps, eps=0.15, min_samples=2)
    agglomerative = cluster_vectors(
        vectors, timestamps, eps=0.15, min_samples=2, algorithm="agglomerative"
    )
    assert dbscan.cluster_count == 2
    assert agglomerative.cluster_count == 2


def test_cluster_quality_reports_intra_similarity():
    vectors = np.vstack([_cluster(4, 3), _cluster(7, 3)])
    timestamps = _timestamps(len(vectors))
    result = cluster_vectors(vectors, timestamps, eps=0.15, min_samples=2)
    quality = cluster_quality(vectors, result.labels)
    assert quality["clusters"] == 2
    assert quality["avg_intra_similarity"] > 0.9
