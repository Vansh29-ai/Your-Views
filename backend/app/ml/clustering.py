"""Batch clustering over stored embeddings.

Used for (re)building events over a window of already-collected articles and for offline
quality evaluation. Incremental ingestion uses ``event_matcher`` instead; this module is the
batch counterpart and shares the same vector space and time constraints.

DBSCAN is the default (density based, no need to pre-specify cluster count, explicit noise).
Agglomerative clustering is available for comparison. Both operate on cosine distance with a
post-hoc time-window split so a cluster cannot span unrelated days.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from app.ml.similarity import cosine_matrix


@dataclass
class ClusterResult:
    labels: np.ndarray  # -1 = noise
    algorithm: str
    eps: float
    min_samples: int
    cluster_count: int

    def clusters(self) -> list[list[int]]:
        groups: dict[int, list[int]] = {}
        for index, label in enumerate(self.labels):
            if label < 0:
                continue
            groups.setdefault(int(label), []).append(index)
        return [groups[key] for key in sorted(groups)]


def _split_by_time(
    indices: list[int],
    timestamps: list[datetime],
    *,
    window_hours: float,
) -> list[list[int]]:
    if len(indices) <= 1 or window_hours <= 0:
        return [indices] if indices else []
    ordered = sorted(indices, key=lambda i: timestamps[i])
    groups: list[list[int]] = [[ordered[0]]]
    for index in ordered[1:]:
        previous = groups[-1][-1]
        gap = abs((timestamps[index] - timestamps[previous]).total_seconds()) / 3600.0
        if gap > window_hours:
            groups.append([index])
        else:
            groups[-1].append(index)
    return groups


def cluster_vectors(
    vectors: np.ndarray,
    timestamps: list[datetime],
    *,
    eps: float = 0.24,
    min_samples: int = 2,
    time_window_hours: float = 72.0,
    algorithm: str = "dbscan",
) -> ClusterResult:
    """Cluster L2-normalised vectors; returns labels aligned with the input rows."""
    count = len(vectors)
    if count == 0:
        return ClusterResult(np.zeros(0, dtype=int), algorithm, eps, min_samples, 0)
    if count == 1:
        return ClusterResult(np.full(1, -1, dtype=int), algorithm, eps, min_samples, 0)

    if algorithm == "agglomerative":
        from sklearn.cluster import AgglomerativeClustering

        model = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=eps,
        )
        raw_labels = model.fit_predict(np.asarray(vectors, dtype=np.float64))
    else:
        from sklearn.cluster import DBSCAN

        model = DBSCAN(metric="cosine", eps=eps, min_samples=min_samples)
        raw_labels = model.fit_predict(np.asarray(vectors, dtype=np.float64))

    labels = np.full(count, -1, dtype=int)
    next_label = 0
    for label in sorted(set(int(value) for value in raw_labels)):
        if label < 0:
            continue
        members = [int(i) for i in np.where(raw_labels == label)[0]]
        for group in _split_by_time(members, timestamps, window_hours=time_window_hours):
            if len(group) >= min_samples:
                for index in group:
                    labels[index] = next_label
                next_label += 1
    return ClusterResult(
        labels=labels,
        algorithm=algorithm,
        eps=eps,
        min_samples=min_samples,
        cluster_count=next_label,
    )


def cluster_quality(vectors: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    """Internal quality diagnostics (no ground truth needed)."""
    clusters = [group for group in _groups(labels) if len(group) >= 2]
    if not clusters:
        return {"clusters": 0, "avg_size": 0.0, "avg_intra_similarity": 0.0, "avg_max_similarity": 0.0}
    similarities = cosine_matrix(vectors)
    intra: list[float] = []
    maxima: list[float] = []
    for group in clusters:
        if len(group) < 2:
            continue
        sub = similarities[np.ix_(group, group)]
        upper = sub[np.triu_indices_from(sub, k=1)]
        intra.append(float(np.mean(upper)))
        maxima.append(float(np.max(upper)))
    return {
        "clusters": len(clusters),
        "avg_size": round(float(np.mean([len(g) for g in clusters])), 2),
        "avg_intra_similarity": round(float(np.mean(intra)) if intra else 0.0, 4),
        "avg_max_similarity": round(float(np.mean(maxima)) if maxima else 0.0, 4),
    }


def _groups(labels: np.ndarray) -> list[list[int]]:
    groups: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        if int(label) >= 0:
            groups.setdefault(int(label), []).append(index)
    return list(groups.values())
