"""Named-entity extraction.

Primary path: spaCy ``en_core_web_sm`` (PERSON / ORG / GPE / LOC / EVENT / NORP / FAC).
Fallback: a deterministic capitalised-sequence extractor so the pipeline keeps working on
machines where the spaCy model has not been downloaded. The fallback is lexical, not random;
it is labelled as such in the extraction method so the UI can stay honest about it.
"""

from __future__ import annotations

import re
import threading

from app.utils.text import STOPWORDS, clean_whitespace

ENTITY_LABELS = {"PERSON", "ORG", "GPE", "LOC", "EVENT", "NORP", "FAC", "PRODUCT"}

_GENERIC = {
    "the",
    "a",
    "an",
    "this",
    "that",
    "these",
    "those",
    "mr",
    "mrs",
    "ms",
    "dr",
    "president",
    "prime minister",
    "government",
    "minister",
    "officials",
    "police",
    "report",
    "reports",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "today",
    "yesterday",
    "tomorrow",
    "new",
    "breaking",
    "exclusive",
    "analysis",
    "opinion",
    "world",
    "news",
    "according",
    "meanwhile",
    "however",
    "but",
    "and",
    "it",
    "he",
    "she",
    "they",
    "we",
    "i",
    "you",
    "who",
    "what",
    "why",
    "how",
    "when",
    "where",
}

_CAP_SEQUENCE = re.compile(
    r"\b([A-Z][A-Za-z'’.\-]{1,}(?:\s+(?:(?:of|the|and|for|de|al|bin|van|von|el|da|di)\s+)?"
    r"[A-Z][A-Za-z'’.\-]{1,}){0,4})"
)
_POSSESSIVE = re.compile(r"'s$")
_TRAILING = re.compile(r"[\s,.;:)\]}]+$")


def _normalise_entity(value: str) -> str:
    value = clean_whitespace(value)
    value = _TRAILING.sub("", value)
    value = _POSSESSIVE.sub("", value)
    value = re.sub(r"^(the|a|an)\s+", "", value, flags=re.I)
    return value.strip()


def _is_useful(value: str) -> bool:
    lowered = value.lower()
    if not value or len(value) < 2 or lowered in _GENERIC:
        return False
    if lowered in STOPWORDS:
        return False
    if all(token.lower() in STOPWORDS or token.lower() in _GENERIC for token in value.split()):
        return False
    if len(value.split()) > 6:
        return False
    if sum(ch.isalpha() for ch in value) < 2:
        return False
    return True


def _dedupe(entities: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for entity in sorted(entities, key=len, reverse=True):
        key = entity.lower()
        if key in seen:
            continue
        if any(key in other.lower().split() or key == other.lower() for other in ordered):
            continue
        seen.add(key)
        ordered.append(entity)
    # Restore a stable, readable order
    return list(dict.fromkeys(sorted(ordered, key=str.lower)))


class EntityExtractor:
    """Thread-safe, lazily-initialised entity extractor."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._nlp = None
        self._attempted = False
        self.method = "regex"

    def _load_spacy(self):  # type: ignore[no-untyped-def]
        if self._attempted:
            return self._nlp
        with self._lock:
            if self._attempted:
                return self._nlp
            self._attempted = True
            try:
                import spacy

                self._nlp = spacy.load("en_core_web_sm", disable=["lemmatizer", "textcat"])
                self.method = "spacy:en_core_web_sm"
            except Exception:  # pragma: no cover - depends on local model availability
                self._nlp = None
                self.method = "regex"
        return self._nlp

    def extract(self, text: str) -> list[str]:
        if not text:
            return []
        nlp = self._load_spacy()
        if nlp is not None:
            doc = nlp(text[:4000])
            entities = [
                _normalise_entity(ent.text)
                for ent in doc.ents
                if ent.label_ in ENTITY_LABELS
            ]
            entities = [entity for entity in entities if _is_useful(entity)]
            if entities:
                return _dedupe(entities)[:24]
        return self._regex_extract(text)

    def _regex_extract(self, text: str) -> list[str]:
        candidates: list[str] = []
        for match in _CAP_SEQUENCE.finditer(clean_whitespace(text)[:4000]):
            candidate = _normalise_entity(match.group(1))
            if _is_useful(candidate):
                candidates.append(candidate)
        return _dedupe(candidates)[:18]


_extractor: EntityExtractor | None = None


def get_entity_extractor() -> EntityExtractor:
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor


def extract_entities(text: str) -> list[str]:
    return get_entity_extractor().extract(text)


def entity_keys(entities: list[str]) -> set[str]:
    return {entity.lower().strip() for entity in entities if entity.strip()}
