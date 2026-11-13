"""Keyword extraction — frequency based, title-weighted, stopword filtered.

Kept intentionally lightweight (no corpus-dependent IDF at article level) so it works for
streaming ingestion and stays deterministic. This is a *lexical emphasis* signal, not a
claim about importance or bias.
"""

from __future__ import annotations

import re

from app.utils.text import STOPWORDS, content_tokens

MIN_KEYWORD_LENGTH = 3
_SUFFIXES = ("ies", "es", "s")


def _singularise(token: str) -> str:
    token = re.sub(r"'s$", "", token).strip("'-")
    if len(token) <= 4:
        return token
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and not token.endswith("ss"):
            stem = token[: -len(suffix)]
            if suffix == "ies":
                stem += "y"
            return stem
    return token


def _tokens(value: str) -> list[str]:
    cleaned: list[str] = []
    for raw in content_tokens(value):
        token = _singularise(raw)
        if len(token) < MIN_KEYWORD_LENGTH:
            continue
        if re.fullmatch(r"\d+", token):
            continue
        cleaned.append(token)
    return cleaned


def extract_keywords(title: str, summary: str = "", *, limit: int = 10) -> list[str]:
    title_tokens = _tokens(title)
    body_tokens = _tokens(summary)
    scores: dict[str, float] = {}
    for token in title_tokens:
        scores[token] = scores.get(token, 0.0) + 2.4
    for token in body_tokens:
        scores[token] = scores.get(token, 0.0) + 1.0
    ranked = sorted(
        ((token, score) for token, score in scores.items() if token not in STOPWORDS),
        key=lambda item: (-item[1], item[0]),
    )
    return [token for token, _ in ranked[:limit]]
