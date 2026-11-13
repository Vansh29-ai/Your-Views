"""Event matching logic — thresholds, corroboration and the topic-vs-event distinction."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from app.config.settings import Settings
from app.ml.event_matcher import EventCandidate, choose_match, evaluate_candidate


def unit_vector(cosine: float) -> np.ndarray:
    """Build a 384-d unit vector whose dot product with the reference vector is ``cosine``."""
    reference = np.zeros(384, dtype=np.float32)
    reference[0] = 1.0
    other = np.zeros(384, dtype=np.float32)
    other[0] = cosine
    other[1] = np.sqrt(max(0.0, 1.0 - cosine**2))
    return other


@pytest.fixture()
def config() -> Settings:
    return Settings(
        strong_similarity=0.74,
        weak_similarity=0.62,
        candidate_window_hours=96,
        weight_similarity=0.62,
        weight_entities=0.22,
        weight_keywords=0.10,
        weight_time=0.06,
    )


def _candidate(cosine: float, *, entities=("Bank of England", "Andrew Bailey"), hours_ago=3) -> EventCandidate:
    return EventCandidate(
        event_id=7,
        centroid=unit_vector(cosine),
        entities={entity.lower() for entity in entities},
        keywords={"interest", "rates", "inflation"},
        last_published_at=datetime.utcnow() - timedelta(hours=hours_ago),
    )


def test_strong_similarity_matches_without_entity_evidence(config):
    decision = choose_match(
        embedding=unit_vector(1.0),
        entities=[],
        keywords=[],
        published_at=datetime.utcnow(),
        candidates=[_candidate(0.8)],
        config=config,
    )
    assert decision.matched
    assert decision.method == "semantic"
    assert decision.event_id == 7


def test_weak_similarity_needs_entity_corroboration(config):
    decision = choose_match(
        embedding=unit_vector(1.0),
        entities=["Bank of England", "Andrew Bailey", "Threadneedle Street"],
        keywords=["interest", "rates", "inflation"],
        published_at=datetime.utcnow(),
        candidates=[_candidate(0.66)],
        config=config,
    )
    assert decision.matched
    assert decision.method == "corroborated"


def test_weak_similarity_without_entities_is_rejected(config):
    decision = choose_match(
        embedding=unit_vector(1.0),
        entities=[],
        keywords=["election"],
        published_at=datetime.utcnow(),
        candidates=[_candidate(0.66)],
        config=config,
    )
    assert not decision.matched
    assert decision.reason == "no_candidate_above_threshold"


def test_disjoint_entities_raise_the_threshold(config):
    candidate = _candidate(0.78, entities=("Narendra Modi", "Bharatiya Janata Party"))
    decision = evaluate_candidate(
        embedding=unit_vector(1.0),
        entities={"keir starmer", "labour party"},
        keywords={"election", "campaign"},
        published_at=datetime.utcnow(),
        candidate=candidate,
        config=config,
    )
    assert decision is not None
    assert not decision.matched
    assert decision.reason == "entity_conflict"


def test_time_window_excludes_old_events(config):
    decision = choose_match(
        embedding=unit_vector(1.0),
        entities=[],
        keywords=[],
        published_at=datetime.utcnow(),
        candidates=[_candidate(0.95, hours_ago=24 * 10)],
        config=config,
    )
    assert not decision.matched


def test_best_candidate_wins(config):
    decision = choose_match(
        embedding=unit_vector(1.0),
        entities=[],
        keywords=[],
        published_at=datetime.utcnow(),
        candidates=[_candidate(0.75), _candidate(0.88), _candidate(0.7)],
        config=config,
    )
    assert decision.matched
    assert decision.similarity == pytest.approx(0.88, abs=1e-5)
