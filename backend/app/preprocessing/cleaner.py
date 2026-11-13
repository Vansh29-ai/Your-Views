"""Cleaning + assembly of a validated, hash-addressed article draft."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.ml.entities import extract_entities
from app.preprocessing.keywords import extract_keywords
from app.preprocessing.normalizer import normalize_entry
from app.preprocessing.validator import ValidationResult, validate_article
from app.utils.text import (
    canonicalize_url,
    clean_whitespace,
    sha256_hex,
    simhash_hex,
    strip_html,
    title_key,
)


@dataclass
class ArticleDraft:
    publisher_id: str
    publisher_name: str
    title: str
    summary: str
    content: str
    url: str
    canonical_url: str
    url_hash: str
    content_hash: str
    simhash: str
    published_at: datetime
    category: str
    language: str
    author: str | None
    image_url: str | None
    entities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    word_count: int = 0
    tags: list[str] = field(default_factory=list)

    @property
    def embedding_text(self) -> str:
        """Semantic input: headline carries the most event-specific signal, then the lede."""
        parts = [self.title]
        if self.summary:
            parts.append(self.summary)
        text = " — ".join(part for part in parts if part)
        if len(text) < 80 and self.content:
            text = f"{text} {self.content[:400]}"
        return text[:1600]

    @property
    def browser_title(self) -> str:
        return clean_whitespace(self.title)


def clean_entry(
    entry,
    *,
    publisher_id: str,
    publisher_name: str,
    publisher_names: list[str] | None = None,
    fallback_timestamp: datetime | None = None,
) -> tuple[ArticleDraft | None, ValidationResult | None, str | None]:
    """Normalise a feed entry into a draft, or explain why it was rejected.

    Returns ``(draft, validation, duplicate_key)``. The duplicate key is only informative
    here; the caller performs the database-backed duplicate check.
    """
    payload = normalize_entry(
        entry,
        publisher_name=publisher_name,
        publisher_names=publisher_names or [publisher_name],
    )
    if fallback_timestamp is not None:
        payload["published_at"] = payload["published_at"] or fallback_timestamp

    title = clean_whitespace(strip_html(payload["title"]))
    summary = clean_whitespace(strip_html(payload["summary"]))
    content = clean_whitespace(strip_html(payload["content"]))
    if not content:
        content = summary
    if summary and content and content.startswith(summary[:60]):
        content = content
    elif summary and not content:
        content = summary

    validation = validate_article(
        title=title,
        summary=summary,
        content=content,
        url=payload["url"],
        published_at=payload["published_at"],
    )
    if not validation.ok:
        return None, validation, None

    canonical = canonicalize_url(payload["url"])
    url_hash = sha256_hex(canonical)

    # Content fingerprint excludes the publisher-specific dek formatting differences.
    fingerprint_source = f"{title_key(title)}\n{title_key(summary)}"
    content_hash = sha256_hex(fingerprint_source)
    near_hash = simhash_hex(f"{title} {summary}")

    entity_source = f"{title}. {summary}"
    draft = ArticleDraft(
        publisher_id=publisher_id,
        publisher_name=publisher_name,
        title=title,
        summary=summary,
        content=content,
        url=payload["url"],
        canonical_url=canonical,
        url_hash=url_hash,
        content_hash=content_hash,
        simhash=near_hash,
        published_at=payload["published_at"],
        category=payload["category"],
        language=payload["language"],
        author=payload["author"],
        image_url=payload["image_url"],
        entities=extract_entities(entity_source),
        keywords=extract_keywords(title, summary),
        word_count=len(content.split()),
        tags=payload.get("tags", []),
    )
    return draft, None, url_hash
