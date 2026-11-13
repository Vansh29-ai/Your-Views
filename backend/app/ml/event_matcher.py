"""Incremental article → event assignment.

Embedding similarity alone over-merges broad topics ("two different elections"). The matcher
therefore combines four signals and applies hard corroboration rules:

* semantic similarity to the event centroid,
* shared named entities (people / organisations / places),
* shared event keywords,
* publication-time proximity.

An article joins an existing event only when the evidence is strong, or medium-strength but
corroborated by specific shared entities. Conflicting entity sets raise the bar further.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from app.config.settings import Settings
from app.ml.similarity import cosine_similarity


@dataclass
class EventCandidate:
    event_id: int
    centroid: np.ndarray | None
    entities: set[str]
    keywords: set[str]
    last_published_at: datetime


@dataclass
class MatchDecision:
    event_id: int | None
    score: float = 0.0
    similarity: float = 0.0
    entity_overlap: float = 0.0
    keyword_overlap: float = 0.0
    time_score: float = 0.0
    shared_entities: int = 0
    method: str = "new_event"
    reason: str = "no_candidate_above_threshold"

    @property
    def matched(self) -> bool:
        return self.event_id is not None


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _containment(left: set[str], right: set[str]) -> float:
    """How much of the smaller set is shared — robust when event sets are large."""
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _time_score(delta_hours: float, window_hours: float) -> float:
    if window_hours <= 0:
        return 0.0
    return max(0.0, 1.0 - (delta_hours / window_hours))


def evaluate_candidate(
    *,
    embedding: np.ndarray | None,
    entities: set[str],
    keywords: set[str],
    published_at: datetime,
    candidate: EventCandidate,
    config: Settings,
) -> MatchDecision | None:
    if embedding is None or candidate.centroid is None:
        return None
    delta_hours = abs((published_at - candidate.last_published_at).total_seconds()) / 3600.0
    if delta_hours > config.candidate_window_hours:
        return None

    similarity = cosine_similarity(embedding, candidate.centroid)
    shared = entities & candidate.entities
    shared_count = len(shared)
    entity_overlap = _jaccard(entities, candidate.entities)
    keyword_overlap = _containment(keywords, candidate.keywords)
    time_score = _time_score(delta_hours, config.candidate_window_hours)

    total_weight = (
        config.weight_similarity
        + config.weight_entities
        + config.weight_keywords
        + config.weight_time
    ) or 1.0
    composite = (
        config.weight_similarity * similarity
        + config.weight_entities * entity_overlap
        + config.weight_keywords * keyword_overlap
        + config.weight_time * time_score
    ) / total_weight

    # Guard: two articles with substantive but disjoint entity sets are probably different
    # events that share a topic (e.g. two separate elections, two separate attacks).
    entity_conflict = len(entities) >= 2 and len(candidate.entities) >= 2 and shared_count == 0
    strong_threshold = config.strong_similarity + (0.08 if entity_conflict else 0.0)

    strong = similarity >= strong_threshold
    corroborated = (
        not entity_conflict
        and similarity >= config.weak_similarity
        and (
            (shared_count >= 2 and keyword_overlap >= 0.2)
            or (shared_count >= 1 and keyword_overlap >= 0.34)
        )
    )
    if not (strong or corroborated):
        return MatchDecision(
            event_id=None,
            score=composite,
            similarity=similarity,
            entity_overlap=entity_overlap,
            keyword_overlap=keyword_overlap,
            time_score=time_score,
            shared_entities=shared_count,
            method="rejected",
            reason="entity_conflict" if entity_conflict else "below_threshold",
        )

    return MatchDecision(
        event_id=candidate.event_id,
        score=composite,
        similarity=similarity,
        entity_overlap=entity_overlap,
        keyword_overlap=keyword_overlap,
        time_score=time_score,
        shared_entities=shared_count,
        method="semantic" if strong else "corroborated",
        reason="strong_similarity" if strong else "corroborated_similarity",
    )


def choose_match(
    *,
    embedding: np.ndarray | None,
    entities: list[str],
    keywords: list[str],
    published_at: datetime,
    candidates: list[EventCandidate],
    config: Settings,
) -> MatchDecision:
    entity_set = {entity.lower() for entity in entities if entity}
    keyword_set = {keyword.lower() for keyword in keywords if keyword}
    best: MatchDecision | None = None
    for candidate in candidates:
        decision = evaluate_candidate(
            embedding=embedding,
            entities=entity_set,
            keywords=keyword_set,
            published_at=published_at,
            candidate=candidate,
            config=config,
        )
        if decision is None or not decision.matched:
            continue
        if best is None or decision.score > best.score:
            best = decision
    if best is not None:
        return best
    return MatchDecision(event_id=None, method="new_event", reason="no_candidate_above_threshold")
