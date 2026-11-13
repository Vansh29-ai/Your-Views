"""Vector similarity helpers (cosine on L2-normalised vectors)."""

from __future__ import annotations

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None or a.size == 0 or b.size == 0 or a.shape != b.shape:
        return 0.0
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.clip(np.dot(a, b) / denom, -1.0, 1.0))


def cosine_matrix(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return np.zeros((0, 0), dtype=np.float32)
    matrix = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalised = matrix / norms
    return np.clip(normalised @ normalised.T, -1.0, 1.0)


def centroid(vectors: np.ndarray) -> np.ndarray:
    if len(vectors) == 0:
        return np.zeros(vectors.shape[1] if vectors.ndim > 1 else 0, dtype=np.float32)
    centre = np.mean(vectors, axis=0)
    norm = float(np.linalg.norm(centre))
    if norm > 0:
        centre = centre / norm
    return centre.astype(np.float32)


def top_k(scores: np.ndarray, k: int) -> list[int]:
    if len(scores) == 0:
        return []
    k = min(k, len(scores))
    return list(np.argsort(-scores)[:k])
