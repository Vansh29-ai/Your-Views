"""RSS collector tests using httpx.MockTransport (no network)."""

from __future__ import annotations

import httpx
import pytest

from app.collectors.rss_collector import RSSCollector
from app.collectors.source_manager import FeedDefinition

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Parliament approves national budget after marathon debate</title>
      <link>https://example.com/a</link>
      <description>&lt;p&gt;The budget passed with a narrow majority.&lt;/p&gt;</description>
      <pubDate>Thu, 13 Nov 2026 08:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Second item about an entirely different subject</title>
      <link>https://example.com/b</link>
      <description>Something else entirely.</description>
      <pubDate>Thu, 13 Nov 2026 07:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def _feed() -> FeedDefinition:
    return FeedDefinition(id="test-feed", publisher_id="test", url="https://example.com/rss", category="World")


async def test_fetch_feed_parses_entries_and_stamps_category():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=RSS, headers={"Content-Type": "application/rss+xml"})

    async with RSSCollector(client=httpx.AsyncClient(transport=httpx.MockTransport(handler))) as collector:
        result = await collector.fetch_feed(_feed())

    assert result.ok
    assert result.status == "ok"
    assert len(result.entries) == 2
    assert result.entries[0]["_feed_category"] == "World"
    assert result.entries[0]["title"].startswith("Parliament")


async def test_conditional_get_handles_304():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("If-None-Match") == '"abc"'
        return httpx.Response(304)

    async with RSSCollector(client=httpx.AsyncClient(transport=httpx.MockTransport(handler))) as collector:
        result = await collector.fetch_feed(_feed(), etag='"abc"')

    assert result.status == "not_modified"
    assert result.entries == []


async def test_http_errors_are_reported_not_raised():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with RSSCollector(client=httpx.AsyncClient(transport=httpx.MockTransport(handler))) as collector:
        result = await collector.fetch_feed(_feed())

    assert not result.ok
    assert result.status == "error"
    assert result.http_status == 404


async def test_malformed_xml_without_entries_is_an_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not a feed</html>", headers={"Content-Type": "text/html"})

    async with RSSCollector(client=httpx.AsyncClient(transport=httpx.MockTransport(handler))) as collector:
        result = await collector.fetch_feed(_feed())

    assert result.status == "error"
    assert result.error


@pytest.mark.parametrize("status", [500, 502])
async def test_server_errors_retry_then_fail(monkeypatch, status):
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(status)

    from app.config.settings import settings

    monkeypatch.setattr(settings, "request_retries", 1)

    async with RSSCollector(client=httpx.AsyncClient(transport=httpx.MockTransport(handler))) as collector:
        result = await collector.fetch_feed(_feed())

    assert result.status == "error"
    assert result.http_status == status
    assert attempts["count"] == 2
