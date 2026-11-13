"""Article validation rules — reject unusable feed entries before they reach the ML stage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from app.utils.text import content_tokens

MIN_TITLE_CHARS = 16
MAX_TITLE_CHARS = 320
MIN_TEXT_CHARS = 70
MAX_AGE_DAYS = 30
GENERIC_TITLES = {
    "news",
    "latest news",
    "breaking news",
    "top stories",
    "video",
    "live",
    "watch",
    "home",
    "world news",
    "untitled",
}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str | None = None

    def __bool__(self) -> bool:  # convenience
        return self.ok


def validate_article(
    *,
    title: str,
    summary: str,
    content: str,
    url: str,
    published_at: datetime | None,
    now: datetime | None = None,
) -> ValidationResult:
    now = now or datetime.utcnow()
    title = (title or "").strip()
    url = (url or "").strip()

    if not title:
        return ValidationResult(False, "missing_title")
    if len(title) < MIN_TITLE_CHARS:
        return ValidationResult(False, "title_too_short")
    if len(title) > MAX_TITLE_CHARS:
        return ValidationResult(False, "title_too_long")
    if title.lower().strip(" .!-") in GENERIC_TITLES:
        return ValidationResult(False, "generic_title")
    if len(content_tokens(title)) < 3:
        return ValidationResult(False, "title_not_informative")

    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc or "." not in parts.netloc:
        return ValidationResult(False, "invalid_url")

    body = f"{summary or ''} {content or ''}".strip()
    if len(body) < MIN_TEXT_CHARS:
        return ValidationResult(False, "insufficient_text")
    if len(content_tokens(body)) < 12:
        return ValidationResult(False, "insufficient_text")

    if published_at is None:
        return ValidationResult(False, "missing_timestamp")
    if published_at > now + timedelta(hours=12):
        return ValidationResult(False, "future_timestamp")
    if published_at < now - timedelta(days=MAX_AGE_DAYS):
        return ValidationResult(False, "stale_article")

    non_latin = sum(1 for char in title if ord(char) > 0x024F and char.isalpha())
    if non_latin > max(4, len(title) * 0.25):
        return ValidationResult(False, "unsupported_language")

    return ValidationResult(True)
