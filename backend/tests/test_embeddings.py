"""Embedding provider tests (deterministic lexical backend + optional live model)."""

from __future__ import annotations

import os

import numpy as np
import pytest

from app.ml.embeddings import (
    HashingEmbedder,
    embedding_service,
    pack_vector,
    text_fingerprint,
    unpack_vector,
)


@pytest.fixture(scope="module")
def embedder() -> HashingEmbedder:
    return HashingEmbedder()


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def test_vectors_are_normalised_and_deterministic(embedder):
    text = "Government announces major economic reforms after cabinet meeting"
    first = embedder.encode([text])[0]
    second = embedder.encode([text])[0]
    assert np.allclose(first, second)
    assert abs(np.linalg.norm(first) - 1.0) < 1e-5
    assert first.shape == (384,)


def test_similar_texts_score_higher_than_unrelated_texts(embedder):
    a, b, c = embedder.encode(
        [
            "Bank of England raises interest rates to fight inflation",
            "UK central bank lifts interest rates as inflation persists",
            "Late wicket seals dramatic cricket victory in Mumbai",
        ]
    )
    assert cosine(a, b) > cosine(a, c)
    assert cosine(a, b) > 0.35


def test_pack_unpack_roundtrip():
    vector = np.linspace(-0.5, 0.5, 384, dtype=np.float32)
    packed = pack_vector(vector)
    restored = unpack_vector(packed, 384)
    assert restored is not None
    assert np.allclose(vector, restored)
    assert unpack_vector(packed, 12) is None
    assert unpack_vector(None, 384) is None


def test_text_fingerprint_changes_with_text():
    assert text_fingerprint("alpha") == text_fingerprint("alpha")
    assert text_fingerprint("alpha") != text_fingerprint("beta")


@pytest.mark.skipif(
    os.environ.get("YV_TEST_LIVE_MODEL") != "1",
    reason="Set YV_TEST_LIVE_MODEL=1 to exercise the downloaded sentence-transformer.",
)
def test_live_minilm_separates_paraphrase_from_unrelated():
    info = embedding_service.info
    assert info.semantic
    a, b, c = embedding_service.encode(
        [
            "Government announces major economic reforms",
            "New economic policies introduced by the government",
            "Heavy rain disrupts flights across northern India",
        ]
    )
    assert cosine(a, b) > cosine(a, c) + 0.15
