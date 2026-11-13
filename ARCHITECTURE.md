# YOUR VIEWS — Architecture

This document describes how the system actually works, the decisions behind it, and the
trade-offs that were made deliberately.

## 1. Design goals

1. **Event-centric, not article-centric.** The primary object is an event that groups reporting
   from different publishers. Everything else exists to build, query or display that object.
2. **Real signals, no theatre.** No random clustering, no hardcoded event ids, no invented bias
   scores. Every number shown in the UI is computed from stored data.
3. **Legible matching.** A reader should be able to understand why two articles were grouped:
   semantic similarity, shared entities, shared keywords, time proximity.
4. **Operable.** One process, one database, health surfaces, feed-level failure isolation,
   re-clustering and calibration tools.
5. **Extensible sources.** Adding a publisher is a registry change, not a pipeline change.

## 2. System shape

```
┌────────────────────────────── FastAPI process ──────────────────────────────┐
│                                                                             │
│  asyncio scheduler ──► IngestionService ──► RSSCollector (async, bounded)   │
│                              │                                             │
│                              ├── cleaner / normaliser / validator          │
│                              ├── deduplicator (URL, exact, SimHash)         │
│                              ├── EmbeddingService (MiniLM 384-d)            │
│                              └── EventMatcher ──► EventService              │
│                                                                             │
│  Routers: events, articles, publishers, search, stats, admin, health        │
│  Search: SQLite FTS5 (bm25), LIKE fallback                                  │
│  Storage: SQLAlchemy 2.0 → SQLite (WAL) or PostgreSQL                       │
│                                                                             │
│  SPA: serves frontend/dist with client-side routing fallback                │
└─────────────────────────────────────────────────────────────────────────────┘
```

The same process serves the API and the compiled React SPA in production; in development Vite
runs separately and proxies `/api` to port 8000.

## 3. Data model

```
publishers 1──n articles n──1 events
                    │
                    └── feed_health (per feed)
ingestion_runs (per collection cycle)
search_documents (1:1 with events, mirrored into FTS5)
```

**`articles`** stores cleaned title/summary/content, canonical URL + SHA-256 URL hash, content
fingerprint, 64-bit SimHash, publication/fetch timestamps, category, language, entities,
keywords, word count, and the packed float32 embedding plus the model name/dimension that
produced it.

**`events`** stores the representative headline (earliest report), summary, category, article /
publisher counts, publisher slugs, keywords, entities, category set, centroid (packed float32),
embedding model, first/last publication timestamps and a lead article reference.

Why store the centroid? It makes incremental matching an O(1) vector operation per event instead
of recomputing an average over all member articles. The centroid is updated incrementally
(`(centroid * n + vector) / (n + 1)`, renormalised) and fully recomputed after batch
re-clustering.

Embeddings are stored next to the model name that produced them. Matching only considers
candidates with the same `embedding_model`, so a provider change can never mix vector spaces.

## 4. Ingestion pipeline

1. **Registry load.** `config/sources.json` defines publishers, feeds, categories, access type
   and optional per-feed timeouts. `SourceManager` seeds the `publishers` table.
2. **Fetch.** All feeds are fetched concurrently (semaphore 5, 0–350 ms jitter) with a browser-like
   user agent, conditional `If-None-Match`/`If-Modified-Since`, per-feed timeout, two retries
   with backoff and per-feed error isolation. `304` is a success with zero new items.
3. **Clean.** HTML stripping, entity decoding, whitespace normalisation, publisher-suffix removal,
   boilerplate trimming, UTC timestamp normalisation with future/old clamping.
4. **Validate.** Reject missing/short/generic titles, invalid URLs, insufficient text, future or
   older-than-30-day timestamps, non-Latin titles. Rejection reasons are counted in the run.
5. **Deduplicate.**
   - global canonical URL hash (cheap pre-check before validation),
   - exact content fingerprint within a publisher,
   - SimHash (64-bit, token bigrams) Hamming distance ≤ 3 within a publisher.
   Cross-publisher near-duplicates are intentionally **kept**: they are the product's reason to
   exist, not duplicates.
6. **Order.** Surviving drafts are sorted by publication time ascending. Event creation must
   happen before later articles try to join.
7. **Embed.** One batch per run (`EmbeddingService.encode`), L2-normalised, stored with a text
   fingerprint so unchanged text never needs re-embedding.
8. **Match or create.** For each article: load recent candidate events in the same vector space,
   evaluate composite evidence, assign to the best qualifying event or create a new one.
9. **Persist aggregates.** Publisher set, counts, centroid, keyword/entity unions, first/last
   timestamps, representative headline, search document.
10. **Report.** The run row records feeds ok/failed, fetched/new/duplicate/invalid counts, events
    created/updated, duration and the first 40 errors.

A per-article savepoint means one malformed article cannot abort the run. The run commits in
batches of 25 so progress survives a crash.

## 5. Embedding providers

| Provider | Model | Dim | When |
| --- | --- | --- | --- |
| Sentence Transformers | `all-MiniLM-L6-v2` | 384 | Default, if import + model load succeed |
| Deterministic lexical fallback | signed hashing of words, bigrams, char 3–4-grams, sublinear TF, L2 | 384 | Model unavailable and `YV_ALLOW_EMBEDDING_FALLBACK=true` |

The fallback is a real vector space, reproducible and meaningful, but lexical rather than
contextual. `/api/health`, the stats payload and the About page report which backend is active.
No random or mocked vectors exist anywhere in the codebase.

Embedding input is `title — summary` (plus a content excerpt if very short), capped at 1,600
characters. Title and lede carry the most event-specific signal.

## 6. Incremental event matching

For every candidate event within `candidate_window_hours` (default 96):

```
sim      = cosine(article_vector, event_centroid)
ent      = |E_article ∩ E_event| / |E_article ∪ E_event|
kw       = |K_article ∩ K_event| / min(|K_article|, |K_event|)
time     = 1 − hours_since_last_report / window

score    = (0.62·sim + 0.22·ent + 0.10·kw + 0.06·time) / 1.00
```

Decision rules (all thresholds configurable):

- **Strong:** `sim ≥ 0.70` → match (`method = semantic`).
- **Corroborated:** `sim ≥ 0.58` **and** (≥ 2 shared entities with keyword overlap ≥ 0.20, or
  ≥ 1 shared entity with keyword overlap ≥ 0.34) → match (`method = corroborated`).
- **Entity conflict guard:** if both sides have ≥ 2 entities and the intersection is empty, the
  strong threshold rises by 0.08 and corroborated matching is disabled. This is what keeps two
  different elections (e.g. India and the UK) from collapsing into one event.
- Otherwise the article becomes a new event.

The highest-scoring qualifying candidate wins. Every assignment stores its score and method, and
the event page exposes that method in the sidebar ("semantic match", "corroborated match",
"batch cluster", "lead report").

### Calibration

The defaults were not guessed. `scripts/simulate_matching.py` replays stored embeddings through
the matcher inside a transaction, at any threshold pair, and prints the resulting events. Live
cross-publisher pairs showed same-event coverage clustering at 0.70–0.95 and topic-adjacent but
different events around 0.55–0.68, which is why the strong/weak thresholds are 0.70/0.58.
`scripts/evaluate.py` reports pairwise similarity distribution and batch-cluster quality.

## 7. Batch clustering and re-clustering

`ml/clustering.py` implements DBSCAN (default) and agglomerative average-linkage over cosine
distance, followed by a time-window split so a cluster cannot span unrelated days.

`POST /api/admin/recluster` (or `scripts/recluster.py`) rebuilds events inside a window:
events whose last report falls in the window are deleted and their articles — plus unassigned
articles — are re-clustered. Remaining noise articles become single-source events so nothing
disappears from the feed. This operation re-issues event codes; article URLs and content are
untouched.

## 8. Search

Event-first search uses a SQLite FTS5 virtual table (`event_fts`) with the porter tokenizer and
bm25 ranking, synchronised explicitly by `SearchService` on every event change. The indexed
document is title + summary + keywords + entities + publisher slugs. If FTS5 is unavailable, the
service degrades to ranked `LIKE` matching instead of failing.

Search returns event clusters first, then matching headlines and publishers. The front end never
builds a result list from raw article matches alone.

## 9. API and frontend

- Pydantic response models define the public contract (`app/api/schemas.py`).
- Serializers batch-load publishers into a request-scoped directory to avoid N+1 queries.
- All datetimes are naive UTC in the database and ISO-8601 with `Z` on the wire.
- Event list payloads now carry a per-event `image_url` and `image_credit`, selected from every
  member article in one query by `EventService.best_event_images` (see 9.2).
- Search accepts optional `category` and `publisher` filters, applied to the event-cluster results
  while headline and publisher side-results remain available.
- Comparison is client-side state over articles already loaded for the event: select up to four,
  then view aligned headlines, summaries, shared/unique entities and original links.
- Loading skeletons, empty states and error states exist on every data surface. There are no
  dead buttons: the ingestion button, search, filters, sorting, pagination, edition toggle, share
  link and comparison all perform real actions.

### 9.1 The newspaper presentation layer

The front end is a historical newspaper rather than a dashboard:

- **Component language.** `NewspaperMasthead` (front and inner variants), `BreakingNewsStrip`,
  `StoryCard` (lead, feature, column, brief, archive, compact), `ArticleImage` + engraving plate,
  `EditorialSection`, `VintageSearchBar`, `PressRoom`,
  `ArchiveFilters`, `ArchivePagination`, `PublisherArticle`, `ComparisonSpread`, `EmphasisTable`,
  `CoverageLedger`, `DynamicBackdrop`, `NewspaperFooter`.
- **Design tokens.** CSS variables for parchment, secondary paper, faded paper, ink, muted ink,
  rules and oxblood; a `.night` class changes the same variables to warm dark stock. Tailwind
  maps those variables into utilities so components never hardcode hex values.
- **Typography.** Self-hosted WOFF2 files in `frontend/public/fonts`: UnifrakturCook for the
  masthead, Playfair Display for headlines, IM Fell English for lede/body, Libre Baskerville for
  article text and Special Elite for metadata. No runtime font CDN.
- **Texture.** A fixed SVG `feTurbulence` grain layer, a radial vignette and layered paper
  gradients. Print styles remove both.
- **Layout.** The front page is a 12-column broadsheet: lead + also-in-this-edition rail, then
  top stories, world report, editor's picks, two/three desks and the dispatch index. Mobile
  collapses to a single editorial column; navigation wraps into an index rather than a hidden
  hamburger.
- **Responsive rules.** Verified at 1440, 1024, 768 and 390 px. Horizontal overflow is zero at
  every breakpoint; the only wide elements are the ticker and desk strip, both intentionally
  clipped scroll containers.
- **Motion.** One page fade, gentle image reveal, hover ink transitions and a slow ticker.
  `prefers-reduced-motion` disables all of it.

### 9.2 Images and reading atmosphere

1. RSS media (`media:content`, `media:thumbnail`, enclosures) is stored on each article.
2. `EventService.best_event_images` joins member articles and publishers in one query and ranks
   renditions by host: the BBC/ABC/France 24/The Hindu/CNN CDNs are print-worthy, Guardian’s RSS
   supplies a signed 140 px rendition and is treated as a thumbnail, default/social images are
   rejected. Detail pages use the same logic over all articles.
3. The front end upscales known CDNs (`ichef` 240→976, ABC 384→992) and filters placeholder
   images. If no image survives, `ArticleImage` renders a deterministic engraving-style SVG plate
   labelled “decorative plate · no photograph supplied” — never a stock photograph.
4. Event pages place the selected image in a fixed, low-opacity (14%) backdrop behind a parchment
   gradient, with the image itself blurred and sepia-toned. Text sits on an opaque content layer,
   so contrast is unaffected.
5. Images are `loading="lazy"` except the lead photograph, which is eager and high priority, and
   every image has a fixed aspect ratio to prevent layout shift.

## 10. Deliberate trade-offs

**SQLite instead of PostgreSQL by default.** The app must run with one command and no external
services. SQLite with WAL comfortably handles a single-node aggregator and gives transactional
ingestion and FTS5 for free. The service layer is SQLAlchemy-based and largely portable; the
documented production path is PostgreSQL (swap `YV_DATABASE_URL`, add `psycopg`, replace FTS5
with `tsvector` or an external search engine). Multi-worker ingestion would need a queue and a
distributed lock — the current scheduler is intentionally single-process.

**No LLM summarisation.** Event summaries use the lead article's own summary. Generating new
prose would improve polish but introduces hallucination and attribution risk that the product's
"compare, don't adjudicate" stance cannot justify at this stage.

**No bias or sentiment scores.** Lexical emphasis and entity differences are shown as facts about
what was mentioned. Sentiment analysis would imply a judgement the system cannot substantiate.

**Reuters unavailable.** Reuters retired public RSS; the registry marks it as requiring a
licensed API and the UI explains why. Scraping it would violate the project's compliance rule.

**Hashing fallback.** A lexical fallback can produce weaker groupings than MiniLM. It exists so
the pipeline is usable on machines where torch cannot be installed; it is labelled in the UI and
the health endpoint rather than hidden.

## 11. Operational surfaces

- `GET /api/health` — database, FTS, embedder, feed health, last run status.
- `GET /api/admin/status` — running flag, latest run, feed counts.
- `GET /api/admin/runs` — recent run history with counters and errors.
- `GET /api/publishers` — per-feed health, latency, last error, article/event counts.
- Structured logs with timings for fetch, embed and assign phases.
- Scripts: `ingest.py`, `recluster.py`, `reindex.py`, `reprocess_articles.py`, `evaluate.py`,
  `simulate_matching.py`.

## 12. Scaling path

1. Move ingestion to a worker process/queue (Redis/RQ or Celery) with one scheduler leader.
2. PostgreSQL + `pgvector` for approximate nearest-neighbour candidate retrieval instead of
   scanning recent events in Python.
3. Incremental index updates already work; swap FTS5 for OpenSearch if search grows beyond
   SQLite's comfort zone.
4. Cache event list/detail responses (ETag) at the API edge.
5. Add a cross-encoder re-ranking step for borderline similarity pairs, using the entity/time
   evidence as a cheap first stage.
