"""Publisher image helpers shared by API serialisers and services."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit

PLACEHOLDER_PATTERNS = (
    "abc_news_default",
    "placeholder",
    "no-image",
    "no_image",
    "fallback-image",
    "default-social",
)


def image_quality(url: str | None) -> int:
    """Rank publisher image CDNs by the rendition they typically supply."""
    if not url:
        return 0
    lowered = url.lower()
    if any(pattern in lowered for pattern in PLACEHOLDER_PATTERNS):
        return 0
    host = urlsplit(url).netloc.lower()
    if host.endswith(
        (
            "ichef.bbci.co.uk",
            "abcnews.com",
            "abcnewsfe.com",
            "thgim.com",
            "france24.com",
            "cnn.com",
        )
    ):
        return 3
    if host.endswith("guim.co.uk"):
        return 1  # signed 140px rendition
    return 2


def choose_best_image(rows: list[tuple[int, str, str, datetime]]) -> dict[int, tuple[str, str]]:
    """From (event_id, image_url, publisher_name, published_at) rows pick the best per event."""
    best: dict[int, tuple[int, datetime, str, str]] = {}
    for event_id, url, publisher_name, published_at in rows:
        score = image_quality(url)
        if score == 0:
            continue
        current = best.get(event_id)
        if current is None or score > current[0] or (score == current[0] and published_at > current[1]):
            best[event_id] = (score, published_at, url, publisher_name)
    return {event_id: (url, publisher) for event_id, (_, _, url, publisher) in best.items()}
