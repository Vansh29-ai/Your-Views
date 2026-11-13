# YOUR VIEWS — Project Status

_Last updated: 2026-11-13_

## Current phase

**Phase 6 (testing & optimisation) complete. Phase 7 (deployment) implemented and verified
locally.** The application runs end to end on real collected data.

```
Phase 0  Repository analysis ......... done  (empty workspace → greenfield build)
Phase 1  Data collection ............. done  12 publishers / 28 feeds / health + retries
Phase 2  NLP + event clustering ...... done  MiniLM, matcher, DBSCAN, calibration
Phase 3  Backend + database .......... done  FastAPI, SQLite, FTS5, 43 tests
Phase 4  Frontend .................... done  newspaper front end, 5 routes, comparison, day/night
Phase 5  Integration ................. done  real RSS → events → newspaper UI verified in a browser
Phase 6  Testing & optimisation ...... done  584 real articles, re-clustering, calibration, QA
Phase 7  Deployment .................. done* multi-stage Dockerfile, compose, docs

\* Dockerfiles and compose are provided and statically reviewed; the container image itself
could not be built in this environment because the Docker CLI is not installed.
```

## What exists (verified)

### Collection
- [x] Central registry: `backend/app/config/sources.json` (12 publishers, 28 feeds)
- [x] Async RSS collector with conditional GET, per-feed timeout, retries, jitter, 304 handling
- [x] Per-feed health (`feed_health`) and per-run diagnostics (`ingestion_runs`)
- [x] Reuters registered as unavailable (licensed API required) rather than scraped
- [x] Optional licensed-API extension point documented; no fake API adapter
- [x] Graceful handling of malformed XML, timeouts, empty feeds, 4xx/5xx

### Preprocessing
- [x] HTML strip, entity decode, whitespace/unicode normalisation
- [x] Publisher-suffix and boilerplate removal
- [x] UTC timestamp normalisation with future/stale clamping
- [x] Validation: title quality, URL shape, text volume, age, language
- [x] Global canonical URL dedupe + per-publisher exact hash + SimHash near-duplicate
- [x] Named entities (spaCy `en_core_web_sm`, regex fallback) and title-weighted keywords
- [x] Stable article structure and SQL schema

### ML / NLP
- [x] `all-MiniLM-L6-v2` sentence embeddings, batched and L2-normalised
- [x] Embedding provider fallback (deterministic signed hashing) with honest labelling
- [x] Cosine similarity, event centroids, similarity matrix utilities
- [x] Incremental matcher with semantic + entity + keyword + time signals
- [x] Conflict guard against different events that share a topic
- [x] Batch DBSCAN and agglomerative clustering with time-window splitting
- [x] Batch re-clustering API + CLI
- [x] Threshold calibration tooling (`simulate_matching.py`, `evaluate.py`)
- [x] Embeddings reused from storage; no recomputation for unchanged articles

### Backend
- [x] FastAPI app factory, lifespan bootstrap, CORS, gzip, SPA serving
- [x] Events, articles, publishers, search, stats, admin, health endpoints
- [x] Filters (category, publisher, coverage, window), sorting, pagination
- [x] Event detail: articles, timeline, per-publisher emphasis analysis
- [x] FTS5 search with bm25 + LIKE fallback, suggestions
- [x] Run history, source registry, ingestion trigger, re-cluster trigger
- [x] Pydantic response contracts and batched serialisation
- [x] 43 passing tests (unit + integration + HTTP)

### Frontend
- [x] Vintage newspaper masthead, issue number, date, edition line, double rules and category index
- [x] Front page broadsheet: lead dispatch, also-in-this-edition rail, top stories, world report,
      editor's picks, three desks, latest dispatches
- [x] Archive page with desk/publisher filters, ordering, search and roman-numeral pagination
- [x] Event page with dynamic image backdrop, coverage ledger, publisher reports, comparison
      spread and per-publisher emphasis table
- [x] Comparison selection preserved (up to four reports) with aligned/shared terms
- [x] The Index with category and publisher filters, related suggestions, headline results
- [x] Methodology page as an editorial essay with live model/registry state
- [x] Day and Night editions, persisted, adapted palette rather than a generic dark theme
- [x] Self-hosted newspaper typefaces (UnifrakturCook, Playfair, IM Fell, Libre Baskerville,
      Special Elite) and paper grain/vignette
- [x] Publisher image selection, CDN upscaling, sepia/halftone treatment, engraving fallbacks and
      missing-image placeholders
- [x] Responsive verification at 1440, 1024, 768 and 390 px; zero page overflow
- [x] 10 frontend tests + browser QA script with console, network and layout assertions
- [x] No placeholder buttons; all controls perform real actions

### Ops / deployment
- [x] `README.md`, `ARCHITECTURE.md`, this file, `.env.example`
- [x] Multi-stage `Dockerfile` with baked models and SPA
- [x] `docker-compose.yml` with persistent volume + healthcheck
- [x] CLI scripts: ingest, recluster, reindex, reprocess, evaluate, simulate
- [x] Structured logging + health endpoints
- [x] Optional API key for write/admin endpoints

## Redesign — vintage newspaper (completed)

A complete visual redesign of the front end; the API, database, ingestion and ML remained
untouched except for two additive changes (event images and search filters).

- [x] Paper palette from the brief: `#E8D6B5`, `#DCC49A`, `#241B14`, `#594735`, `#806747`,
      `#CDB58D`, plus an oxblood ink accent.
- [x] Masthead in UnifrakturCook with volume/issue, date, tagline and double rules.
- [x] 12-column broadsheet front page; no dashboard cards, gradients, glass or neon.
- [x] Image-led story cards with 16:9 / 4:3 / 3:2 plates, halftone overlay and sepia finish.
- [x] Dynamic event backdrop using the event's own image at 14% behind a parchment wash.
- [x] Engraving fallback plates with deterministic motifs for publishers without images.
- [x] Newspaper comparison spread and emphasis table; all comparison functionality preserved.
- [x] Day/Night editions and print styles.
- [x] Responsive navigation wraps into a newspaper index rather than a hidden menu.
- [x] Production build, 43 backend tests, 10 frontend tests and browser QA all pass.

Key new files: `NewspaperMasthead`, `BreakingNewsStrip`, `StoryCard`, `ArticleImage`,
`EditorialSection`, `PressRoom`, `ArchiveFilters`, `ArchivePagination`, `PublisherArticle`,
`ComparisonSpread`, `EmphasisTable`, `CoverageLedger`, `DynamicBackdrop`, `NewspaperFooter`,
`frontend/public/fonts/*`, `backend/app/utils/images.py`.

## Live data snapshot

From the verified local runs (11 publishers active, ~5 days of coverage):

| Metric | Value |
| --- | --- |
| Articles stored | 584 |
| Events built | 485 |
| Multi-source events | 21 |
| Publishers reporting | 10 of 12 |
| Feeds healthy | 25 of 28 |
| Largest event | 8 publishers / 40 reports (Nvidia CEO resignation) |
| Second-largest | 7 publishers / 12 reports (US–Russia–Ukraine talks) |
| Embedding backend | sentence-transformers / all-MiniLM-L6-v2 / 384-d |
| Ingestion run 1 | 651 items fetched, 565 new, 43 duplicates, 43 invalid, 96 s |
| Ingestion run 2 (incremental) | 561 fetched, 19 new, 501 duplicates, 18 new events, 165 s |

Run 2 is the important one: it proves deduplication and incremental assignment prevent
re-processing the same reporting while still creating events for genuinely new items. Its longer
runtime is almost entirely CBC retry timeouts.

The three unhealthy feeds are CBC (intermittent read timeouts; per-feed 45 s timeout and fetch
jitter added, still failing from this network). Reuters is intentionally inactive.

## Known issues / limitations

1. **CBC feeds are flaky from this network.** They time out or reset under burst, while direct
   single requests succeed. Per-feed 45 s timeout and fetch jitter were added; a retry may still
   be required. The UI shows the failure instead of hiding it.
2. **Single-source events dominate the corpus.** That is a property of real RSS output, not a
   bug. Trending/coverage sorting surfaces multi-source events first; the dashboard exposes a
   "Multi-source only" filter.
3. **Search indexes event metadata, not full article bodies.** Rare phrase queries can return
   nothing; matching headlines are searched separately by title/summary.
4. **Emphasis analysis is lexical.** It compares entities/keywords, not framing quality,
   sentiment or factual accuracy by design.
5. **Event titles are the earliest headline.** They can be less descriptive than a synthesised
   title. Deliberate: no generated prose, no hallucination risk.
6. **Single-process scheduler.** Multi-worker deployment would need a queue + distributed lock.
7. **Re-clustering re-issues event codes.** Old `/events/EVT_xxxxx` links may 404 after a rebuild.
8. **SQLite is the default.** PostgreSQL path is documented but FTS5 search would need
   replacement.
9. **The Docker image was not built in this environment** (Docker CLI unavailable). The
   Dockerfile/compose are provided; the model-baking and static-build stages are the parts to
   watch on the first real build.
10. **Image availability is publisher-dependent.** 436 of 584 articles have a usable image.
    The Guardian's feed supplies a signed 140 px rendition; some events therefore use a smaller
    photograph than ideal. Default/social images are rejected and fall back to an engraving plate.
11. **GitHub publish is pending.** The workspace contains no `.git` directory, no configured
    remote and no Git executable; the redesign is complete locally but cannot be committed or
    pushed from this environment. See “Publishing to GitHub” below.

## Technical decisions

| Decision | Choice | Why |
| --- | --- | --- |
| Database | SQLite + SQLAlchemy + FTS5 | zero-setup local run, transactional ingest, good enough single-node; Postgres documented |
| Embeddings | MiniLM-L6-v2 (384-d) | spec default; strong quality/speed balance; CPU-friendly |
| Fallback | signed hashing lexical vectors | keeps pipeline functional without torch; labelled honestly |
| Event model | stored centroid + aggregates | O(1) incremental matching and fast event lists |
| Matching | thresholded multi-signal with conflict guard | semantics alone over-merges topics |
| Clustering | DBSCAN default, agglomerative alternative | no k required, explicit noise, time split |
| Summaries | publisher's own lead summary | avoids generated claims |
| Bias/sentiment | not implemented | cannot be substantiated; would mislead |
| Reuters | inactive with reason | public RSS retired; scraping violates compliance |
| Search | event-first FTS5 | matches the product's unit of information |
| Frontend state | TanStack Query | caching/refresh for a read-heavy news app |
| Styling | Tailwind + CSS variables + self-hosted fonts | paper palette, day/night, authentic typography |
| Images | best available publisher photo per event + engraving fallback | visual stories without fake stock imagery |

## Threshold calibration

Live pairwise analysis (413 recent articles, cross-publisher pairs):

- same-event pairs observed at 0.70–0.95 cosine;
- topic-adjacent but different events at 0.55–0.68;
- mean pairwise similarity 0.068, p90 0.192.

Chosen: `strong=0.70`, `weak=0.58`, conflict penalty +0.08, window 96 h, `cluster_eps=0.38`.
Replaying stored embeddings at these values produced the 8-publisher Nvidia event and the
7-publisher Putin/Zelensky event without merging unrelated topics.

## Next tasks (prioritised)

1. Add a cross-encoder verification pass for pairs in the 0.55–0.70 band; measure precision on a
   hand-labelled set of ~200 article pairs.
2. Move ingestion to a worker queue (RQ/Celery) and add a distributed run lock.
3. Add PostgreSQL + pgvector adapter and replace FTS5 with Postgres full-text search.
4. Add per-publisher article counts to the event payload (already computed in emphasis).
5. Publish this redesign to GitHub (blocked locally: no git binary, repository or remote).
6. Add Open Graph images / share cards for event pages.
7. Add a “review queue” for low-confidence assignments (`match_score` is stored, UI does not
   surface it yet).
8. End-to-end Playwright suite in CI (the QA script is local-only today).

## Commands

```powershell
# backend
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# collect / maintain
..\.venv\Scripts\python.exe scripts\ingest.py
..\.venv\Scripts\python.exe scripts\recluster.py --days 7 --eps 0.38
..\.venv\Scripts\python.exe scripts\reprocess_articles.py
..\.venv\Scripts\python.exe scripts\evaluate.py --days 7
..\.venv\Scripts\python.exe scripts\simulate_matching.py --strong 0.70 --weak 0.58

# test
..\.venv\Scripts\python.exe -m pytest

# frontend
cd frontend
pnpm install
pnpm dev
pnpm build
pnpm test
node scripts/qa.mjs http://127.0.0.1:8000
```

## Test / QA evidence

- Backend: `43 passed, 1 skipped` (live-model test gated behind `YV_TEST_LIVE_MODEL=1`).
- Frontend: `3 files, 10 tests passed`.
- Browser QA (Chrome) at **1440, 1024, 768 and 390 px** on the front page, archive, event, search
  and methodology pages:
  - no console errors, page errors or failed requests;
  - `scrollWidth === innerWidth` on every page and breakpoint (no horizontal overflow);
  - all 12 front-page images decode, with only 2 engraving plates for events whose publishers
    supplied no image;
  - dynamic event backdrop present; comparison selection and comparison spread render;
  - day/night edition toggle verified;
  - 40-report event opens with 10 reports visible and a working “reveal more” control.
- Production build: `frontend/dist` served by FastAPI; `/api/health` reports `ok`, FTS available,
  semantic embedder active.
- Data quality spot check: 8-publisher Nvidia event groups BBC, Guardian, NPR, DW, France 24, ABC,
  The Hindu and India Today coverage of the same resignation story.

## Publishing to GitHub

This environment has **no Git executable and no `.git` repository/remote**, so the requested
commit and push could not be performed. Nothing was force-pushed or created remotely.

When Git and the repository URL are available:

```powershell
# 1. Install Git (if needed)
winget install --id Git.Git -e --source winget

# 2. If the repository already exists remotely, clone it and copy this work in;
#    do NOT create a second repository.
git clone <YOUR_REPO_URL> your-views
# copy the redesigned backend/, frontend/, docs/ and root markdown files into it

# 3. Or, if this workspace is the intended repository root:
cd C:\Users\jatin\OneDrive\Desktop\deepseek
git init
git remote add origin <YOUR_REPO_URL>
git add .
git commit -m "feat: redesign YOUR VIEWS with vintage newspaper aesthetic"
git branch -M main
git push -u origin main
```

`.gitignore` already excludes `.venv/`, `backend/data/`, `node_modules/`, `frontend/dist/`,
databases, `.env` files and logs. Authenticate with GitHub Desktop, SSH, or a personal access
token supplied interactively — never place the token in a tracked file.
