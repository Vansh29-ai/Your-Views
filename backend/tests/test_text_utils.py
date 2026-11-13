"""Unit tests for text normalisation, URLs and SimHash."""

from __future__ import annotations

from app.utils.text import (
    canonicalize_url,
    hamming_distance,
    simhash,
    strip_html,
    tokenize,
)


def test_strip_html_removes_scripts_and_tags():
    raw = '<p>Hello <b>world</b><script>alert("x")</script></p>'
    assert strip_html(raw) == "Hello world"


def test_strip_html_decodes_entities():
    assert strip_html("Markets &amp; trade&nbsp;talks") == "Markets & trade talks"


def test_canonicalize_url_strips_tracking_and_www():
    url = "https://www.bbc.co.uk/news/world-123/?utm_source=x&utm_medium=y&ref=home"
    assert canonicalize_url(url) == "https://bbc.co.uk/news/world-123"


def test_canonicalize_url_sorts_query_parameters():
    left = canonicalize_url("https://example.com/a?b=2&a=1")
    right = canonicalize_url("https://example.com/a?a=1&b=2")
    assert left == right


def test_simhash_near_duplicates_and_distinct_texts():
    base = "Government announces major economic reforms after cabinet meeting"
    near = "Government announces major economic reforms after a cabinet meeting"
    unrelated = "Late wicket seals dramatic cricket victory in Mumbai"

    assert hamming_distance(simhash(base), simhash(near)) <= 6
    assert hamming_distance(simhash(base), simhash(unrelated)) > 10


def test_tokenize_is_lowercase_and_punctuation_safe():
    assert tokenize("Markets, Trade & Tariffs!") == ["markets", "trade", "tariffs"]
