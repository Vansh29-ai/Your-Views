"""Shared text helpers: HTML cleaning, URL canonicalisation, hashing, hashing-based SimHash."""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_name",
    "utm_id",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
    "smid",
    "partner",
    "cmpid",
    "ncid",
    "ocid",
    "site",
    "output",
    "ito",
}

BOILERPLATE_MARKERS = (
    "continue reading",
    "read more",
    "sign up for",
    "subscribe to",
    "this article is more than",
    "image source",
    "image caption",
    "getty images",
    "advertisement",
    "all rights reserved",
)

STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are aren't as at be because been before being below
    between both but by can't cannot could couldn't did didn't do does doesn't doing don't down during each few
    for from further had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him
    himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself let's me more most mustn't my
    myself no nor not of off on once only or other ought our ours ourselves out over own same shan't she she'd
    she'll she's should shouldn't so some such than that that's the their theirs them themselves then there there's
    these they they'd they'll they're they've this those through to too under until up very was wasn't we we'd we'll
    we're we've were weren't what what's when when's where where's which while who who's whom why why's with won't
    would wouldn't you you'd you'll you're you've your yours yourself yourselves said says say also new news one two
    three first last year years day days week weeks month months time times amid among since may might must now
    according told tells added including like just still even makes make made get got gets go going come comes
    """.split()
)

_PUNCT_RE = re.compile(r"[“”‘’\"'`´]")
_WS_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")
_CONTROL_RE = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]")
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'\-]+")


def strip_html(value: str | None) -> str:
    """Remove HTML tags/scripts and decode entities without mangling punctuation."""
    if not value:
        return ""
    if "<" not in value and "&" not in value:
        return _WS_RE.sub(" ", value).strip()
    soup = BeautifulSoup(value, "lxml")
    for tag in soup(["script", "style", "noscript", "iframe", "form", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return clean_whitespace(html.unescape(text))


def clean_whitespace(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = _CONTROL_RE.sub(" ", value)
    value = _PUNCT_RE.sub("'", value)
    return _WS_RE.sub(" ", value).strip()


def truncate(value: str | None, limit: int, ellipsis: str = "…") -> str:
    if not value:
        return ""
    value = value.strip()
    if len(value) <= limit:
        return value
    cut = value[: limit - 1].rsplit(" ", 1)[0]
    return (cut or value[: limit - 1]).rstrip(",;:.-") + ellipsis


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "ignore")).hexdigest()


def canonicalize_url(url: str) -> str:
    """Normalise a publisher URL for duplicate detection (not for display)."""
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    scheme = "https" if parts.scheme in {"http", "https", ""} else parts.scheme
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
    ]
    query = urlencode(sorted(query_pairs))
    return urlunsplit((scheme, netloc, path, query, ""))


def tokenize(value: str) -> list[str]:
    return _TOKEN_RE.findall((value or "").lower())


def content_tokens(value: str, *, remove_stopwords: bool = True) -> list[str]:
    tokens = tokenize(value)
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 2]
    return tokens


def _hash64(token: str) -> int:
    digest = hashlib.blake2b(token.encode("utf-8", "ignore"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def simhash(value: str) -> int:
    """64-bit SimHash over token shingles, used for near-duplicate detection."""
    tokens = content_tokens(value)
    if not tokens:
        return 0
    shingles = (
        [" ".join(tokens[i : i + 2]) for i in range(len(tokens) - 1)]
        if len(tokens) > 3
        else tokens
    )
    if not shingles:
        shingles = tokens
    bits = [0] * 64
    for shingle in shingles:
        h = _hash64(shingle)
        for bit in range(64):
            bits[bit] += 1 if (h >> bit) & 1 else -1
    fingerprint = 0
    for bit, weight in enumerate(bits):
        if weight > 0:
            fingerprint |= 1 << bit
    return fingerprint


def hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def simhash_hex(value: str) -> str:
    return f"{simhash(value):016x}"


def title_key(title: str) -> str:
    """Normalised key for exact-duplicate checks."""
    return " ".join(content_tokens(title, remove_stopwords=True))
