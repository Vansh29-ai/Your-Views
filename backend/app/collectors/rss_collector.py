"""Async RSS collector with conditional GET, retries and per-feed diagnostics."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import feedparser
import httpx

from app.collectors.source_manager import FeedDefinition
from app.config.settings import settings

logger = logging.getLogger(__name__)

ACCEPT_HEADER = "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.5"


@dataclass
class FeedFetchResult:
    feed: FeedDefinition
    entries: list[dict] = field(default_factory=list)
    http_status: int | None = None
    status: str = "ok"  # ok | not_modified | error
    error: str | None = None
    latency_ms: int | None = None
    etag: str | None = None
    last_modified: str | None = None
    feed_title: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in {"ok", "not_modified"}


class RSSCollector:
    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._external_client = client
        self._client: httpx.AsyncClient | None = client

    async def __aenter__(self) -> "RSSCollector":
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.request_timeout_seconds),
                follow_redirects=True,
                headers={
                    "User-Agent": settings.user_agent,
                    "Accept": ACCEPT_HEADER,
                    "Accept-Language": "en-US,en;q=0.9",
                },
                http2=False,
            )
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._external_client is None and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_feed(
        self,
        feed: FeedDefinition,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FeedFetchResult:
        if self._client is None:
            raise RuntimeError("RSSCollector must be used as an async context manager")
        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        started = time.perf_counter()
        last_error: str | None = None
        for attempt in range(settings.request_retries + 1):
            try:
                response = await self._client.get(
                    feed.url,
                    headers=headers,
                    timeout=feed.timeout or settings.request_timeout_seconds,
                )
                latency = int((time.perf_counter() - started) * 1000)
                if response.status_code == 304:
                    return FeedFetchResult(
                        feed=feed, status="not_modified", http_status=304, latency_ms=latency,
                        etag=response.headers.get("etag") or etag,
                        last_modified=response.headers.get("last-modified") or last_modified,
                    )
                if response.status_code >= 500:
                    last_error = f"HTTP {response.status_code}"
                    if attempt < settings.request_retries:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                if response.status_code >= 400:
                    return FeedFetchResult(
                        feed=feed, status="error", http_status=response.status_code, latency_ms=latency,
                        error=f"HTTP {response.status_code}",
                    )

                parsed = await asyncio.to_thread(feedparser.parse, response.content)
                entries = list(parsed.get("entries", []))
                for entry in entries:
                    entry["_feed_category"] = feed.display_category
                if not entries:
                    detail = parsed.get("bozo_exception") if parsed.get("bozo") else "no items in feed"
                    return FeedFetchResult(
                        feed=feed, status="error", http_status=response.status_code, latency_ms=latency,
                        error=f"Unusable feed: {detail}",
                    )
                return FeedFetchResult(
                    feed=feed,
                    entries=entries[: settings.max_articles_per_feed],
                    status="ok",
                    http_status=response.status_code,
                    latency_ms=latency,
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                    feed_title=(parsed.get("feed") or {}).get("title"),
                )
            except (httpx.HTTPError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < settings.request_retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
            except Exception as exc:  # pragma: no cover - defensive
                last_error = f"{type(exc).__name__}: {exc}"
                logger.exception("Unexpected failure fetching %s", feed.url)
                break

        return FeedFetchResult(
            feed=feed,
            status="error",
            latency_ms=int((time.perf_counter() - started) * 1000),
            error=last_error or "unknown error",
        )
