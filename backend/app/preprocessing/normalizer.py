"""HTML cleaning and text normalisation for collected feed entries."""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from dateutil import parser as date_parser

from app.utils.text import BOILERPLATE_MARKERS, clean_whitespace, strip_html, truncate

CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    "Politics": ("politic", "election", "government", "parliament", "senate", "congress", "diplomac"),
    "Business": ("business", "econom", "market", "finance", "trade", "company", "stock"),
    "Technology": ("technolog", "tech", "digital", "artificial intelligence", " ai ", "cyber", "startup"),
    "Science": ("science", "research", "space", "climate", "environment", "energy", "health"),
    "Health": ("health", "medic", "hospital", "disease", "vaccine", "pandemic"),
    "Sport": ("sport", "football", "cricket", "olympic", "tennis", "match"),
    "Culture": ("culture", "film", "music", "art", "entertainment", "celebrity"),
    "Conflict": ("war", "conflict", "military", "attack", "strike", "ceasefire", "gaza", "ukraine"),
}

CATEGORY_ALIASES = {
    "world": "World",
    "international": "World",
    "global": "World",
    "news": "World",
    "top stories": "World",
    "home": "World",
    "business": "Business",
    "economy": "Business",
    "markets": "Business",
    "technology": "Technology",
    "tech": "Technology",
    "science": "Science",
    "science and environment": "Science",
    "environment": "Science",
    "climate": "Science",
    "health": "Health",
    "politics": "Politics",
    "us politics": "Politics",
    "sport": "Sport",
    "sports": "Sport",
    "culture": "Culture",
}

_DATE_SUFFIX_RE = re.compile(r"\s*[|–—-]\s*(the hindu|bbc news|cnn|npr|reuters|the guardian)\s*$", re.I)
_ELLIPSES = ("...", "…")


def strip_publisher_suffix(title: str, publisher_names: list[str]) -> str:
    cleaned = clean_whitespace(title)
    cleaned = _DATE_SUFFIX_RE.sub("", cleaned)
    for name in publisher_names:
        suffix = f" - {name}"
        if cleaned.lower().endswith(suffix.lower()):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned


def strip_boilerplate(text: str) -> str:
    if not text:
        return ""
    lowered = text.lower()
    for marker in BOILERPLATE_MARKERS:
        index = lowered.find(marker)
        # Only cut boilerplate that appears late in the text so we do not lose the lede.
        if index > 160:
            text = text[:index]
            lowered = text.lower()
    for ellipsis in _ELLIPSES:
        if text.rstrip().endswith(ellipsis):
            text = text.rstrip()[: -len(ellipsis)]
    return clean_whitespace(text)


def normalize_category(feed_category: str | None, entry_tags: list[str] | None = None) -> str:
    """Map publisher specific feed categories onto the platform taxonomy."""
    candidates = [feed_category or "", *(entry_tags or [])]
    for candidate in candidates:
        value = candidate.strip().lower()
        if value in CATEGORY_ALIASES:
            return CATEGORY_ALIASES[value]
        for category in CATEGORY_RULES:
            if category.lower() == value:
                return category
    haystack = " ".join(candidates).lower()
    for category, needles in CATEGORY_RULES.items():
        if any(needle in f" {haystack} " for needle in needles):
            return category
    return "World"


def parse_datetime(value: Any, *, fallback: datetime | None = None) -> datetime:
    """Parse feed timestamps into naive UTC, clamping implausible values."""
    fallback = fallback or datetime.now(timezone.utc)
    parsed: datetime | None = None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        try:
            parsed = datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            parsed = None
    elif isinstance(value, str) and value.strip():
        try:
            parsed = date_parser.parse(value.strip())
        except (ValueError, OverflowError, TypeError):
            parsed = None
    if parsed is None:
        parsed = fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if parsed > now + timedelta(hours=12):
        parsed = now
    if parsed < now - timedelta(days=45):
        parsed = fallback.replace(tzinfo=None) if fallback.tzinfo else fallback
        parsed = max(parsed, now - timedelta(days=45))
    return parsed


def normalize_entry(entry: Any, *, publisher_name: str, publisher_names: list[str]) -> dict:
    """Turn a feedparser entry into the canonical article payload (pre-validation)."""
    raw_title = entry.get("title") or ""
    title = strip_publisher_suffix(strip_html(html.unescape(raw_title)), publisher_names)
    raw_summary = entry.get("summary") or entry.get("description") or ""
    summary = strip_boilerplate(strip_html(raw_summary))
    raw_content = ""
    if entry.get("content"):
        parts = [part.get("value", "") for part in entry["content"] if isinstance(part, dict)]
        raw_content = " ".join(parts)
    content = strip_boilerplate(strip_html(raw_content or raw_summary))
    if content and summary and content.startswith(summary[:80]):
        # Avoid storing the same paragraph twice.
        content_tail = clean_whitespace(content[len(summary) :])
        content = f"{summary} {content_tail}".strip() if content_tail else summary

    tags = [tag.get("term", "") for tag in entry.get("tags", []) if isinstance(tag, dict)]
    link = entry.get("link") or ""
    author = entry.get("author") or ""
    image_url = _extract_image(entry)

    return {
        "title": truncate(title, 300),
        "summary": truncate(summary, 900),
        "content": truncate(content, 6000),
        "url": link,
        "author": truncate(author, 160) or None,
        "image_url": image_url,
        "published_at": parse_datetime(
            entry.get("published") or entry.get("updated") or entry.get("created")
        ),
        "category": normalize_category(entry.get("_feed_category"), tags),
        "language": "en",
        "tags": tags,
        "publisher_name": publisher_name,
    }


def _extract_image(entry: Any) -> str | None:
    for media in entry.get("media_content", []) or []:
        url = media.get("url")
        if url:
            return url
    for thumb in entry.get("media_thumbnail", []) or []:
        url = thumb.get("url")
        if url:
            return url
    for link in entry.get("links", []) or []:
        if isinstance(link, dict) and link.get("rel") == "enclosure" and "image" in (link.get("type") or ""):
            return link.get("href")
    return None
