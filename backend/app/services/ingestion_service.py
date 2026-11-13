"""End-to-end ingestion: fetch → clean → validate → dedupe → embed → assign to events.

Concurrency model: feeds are fetched concurrently (bounded), then articles are processed
sequentially in publication order. Ordering matters: the first article of an event creates the
event, later articles are matched against it, which is exactly how a live newsroom pipeline
behaves. Embeddings are computed as one batch per run instead of per article.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.collectors.rss_collector import FeedFetchResult, RSSCollector
from app.collectors.source_manager import FeedDefinition, PublisherDefinition, source_manager
from app.config.settings import Settings, settings
from app.database.connection import SessionLocal
from app.database.models import Article, Event, FeedHealth, IngestionRun, utcnow
from app.ml.embeddings import EmbeddingInfo, embedding_service, pack_vector, text_fingerprint, unpack_vector
from app.ml.event_matcher import EventCandidate, choose_match
from app.preprocessing.cleaner import ArticleDraft, clean_entry
from app.preprocessing.deduplicator import DuplicateDetector
from app.services.event_service import EventService
from app.utils.text import canonicalize_url, hamming_distance, sha256_hex

logger = logging.getLogger(__name__)

MAX_STORED_ERRORS = 40


@dataclass
class DraftBundle:
    draft: ArticleDraft
    publisher: PublisherDefinition
    feed: FeedDefinition


@dataclass
class RunCounters:
    feeds_ok: int = 0
    feeds_failed: int = 0
    items_fetched: int = 0
    items_new: int = 0
    items_duplicate: int = 0
    items_invalid: int = 0
    events_created: int = 0
    events_updated: int = 0
    errors: list[dict] = field(default_factory=list)

    def add_error(self, source: str, message: str) -> None:
        if len(self.errors) < MAX_STORED_ERRORS:
            self.errors.append({"source": source, "message": message[:500]})


class IngestionService:
    def __init__(
        self,
        *,
        db_factory: sessionmaker = SessionLocal,
        config: Settings | None = None,
        collector_factory: Callable[[], AbstractAsyncContextManager[RSSCollector]] | None = None,
    ) -> None:
        self.db_factory = db_factory
        self.config = config or settings
        self.collector_factory = collector_factory
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._lock.locked()

    async def run(self, trigger: str = "manual") -> int:
        if self._lock.locked():
            raise RuntimeError("An ingestion run is already in progress")
        async with self._lock:
            return await self._run(trigger)

    # ------------------------------------------------------------------ internals
    async def _run(self, trigger: str) -> int:
        db: Session = self.db_factory()
        counters = RunCounters()
        started_wall = utcnow()
        started_perf = time.perf_counter()
        run = IngestionRun(trigger=trigger, status="running", started_at=started_wall)
        db.add(run)
        db.commit()
        run_id = run.id
        logger.info("Ingestion run %s started (trigger=%s)", run_id, trigger)

        try:
            source_manager.seed_publishers(db)
            db.commit()

            publishers = [p for p in source_manager.publishers if p.rss_feeds]
            feeds = [feed for publisher in publishers for feed in publisher.rss_feeds]
            run.feeds_total = len(feeds)
            db.commit()

            health_by_feed = {
                health.feed_id: health for health in db.scalars(select(FeedHealth)).all()
            }
            results = await self._fetch_all(feeds, health_by_feed)

            bundles: list[DraftBundle] = []
            seen_urls: set[str] = set()
            seen_publisher_content: set[tuple[str, str]] = set()
            publisher_simhashes: dict[str, list[int]] = {}
            duplicates = DuplicateDetector(db)
            fallback_now = utcnow()

            for result in results:
                self._record_health(db, result)
                if result.status == "not_modified":
                    counters.feeds_ok += 1
                    continue
                if not result.ok:
                    counters.feeds_failed += 1
                    counters.add_error(result.feed.id, result.error or "fetch_failed")
                    continue
                counters.feeds_ok += 1
                counters.items_fetched += len(result.entries)

                publisher = source_manager.get_publisher(result.feed.publisher_id)
                if publisher is None:
                    counters.add_error(result.feed.id, "publisher_missing_from_registry")
                    continue
                names = source_manager.publisher_names(publisher.id)

                for entry in result.entries:
                    # Cheap URL-level duplicate check before validation/normalisation.
                    link = entry.get("link") or entry.get("id") or ""
                    canonical_link = canonicalize_url(link)
                    link_hash = sha256_hex(canonical_link) if canonical_link else ""
                    if link_hash and (
                        link_hash in seen_urls or duplicates.url_exists(link_hash)
                    ):
                        counters.items_duplicate += 1
                        continue

                    draft, validation, _ = clean_entry(
                        entry,
                        publisher_id=publisher.id,
                        publisher_name=publisher.name,
                        publisher_names=names,
                        fallback_timestamp=fallback_now,
                    )
                    if draft is None:
                        counters.items_invalid += 1
                        continue
                    if draft.url_hash in seen_urls or duplicates.reason_for(
                        url_hash=draft.url_hash,
                        publisher_id=draft.publisher_id,
                        content_hash=draft.content_hash,
                        simhash_hex=draft.simhash,
                    ):
                        counters.items_duplicate += 1
                        continue
                    content_key = (draft.publisher_id, draft.content_hash)
                    if content_key in seen_publisher_content:
                        counters.items_duplicate += 1
                        continue
                    if self._near_duplicate_in_batch(publisher_simhashes, draft):
                        counters.items_duplicate += 1
                        continue

                    seen_urls.add(draft.url_hash)
                    seen_publisher_content.add(content_key)
                    publisher_simhashes.setdefault(publisher.id, []).append(int(draft.simhash, 16))
                    bundles.append(DraftBundle(draft=draft, publisher=publisher, feed=result.feed))

            logger.info("Cleaning complete: %s candidates ready for embedding", len(bundles))
            self._persist_run(db, run, counters)
            db.commit()

            if bundles:
                await self._embed_and_assign(db, run, counters, bundles)

            empty_purged = EventService(db, self.config).purge_empty_events()
            if empty_purged:
                logger.info("Purged %s empty events", empty_purged)

            run.feeds_ok = counters.feeds_ok
            run.feeds_failed = counters.feeds_failed
            run.items_fetched = counters.items_fetched
            run.items_new = counters.items_new
            run.items_duplicate = counters.items_duplicate
            run.items_invalid = counters.items_invalid
            run.events_created = counters.events_created
            run.events_updated = counters.events_updated
            run.errors = counters.errors
            run.status = "completed_with_errors" if counters.feeds_failed else "completed"
            run.finished_at = utcnow()
            run.duration_ms = int((time.perf_counter() - started_perf) * 1000)
            db.commit()
            logger.info(
                "Ingestion run %s %s: +%s articles, %s feeds ok, %s failed, %sms",
                run_id, run.status, counters.items_new, counters.feeds_ok, counters.feeds_failed,
                run.duration_ms,
            )
            return run_id
        except Exception as exc:
            logger.exception("Ingestion run %s failed", run_id)
            db.rollback()
            failed = db.get(IngestionRun, run_id)
            if failed is not None:
                failed.status = "failed"
                failed.finished_at = utcnow()
                failed.duration_ms = int((time.perf_counter() - started_perf) * 1000)
                failed.errors = [*counters.errors, {"source": "pipeline", "message": f"{type(exc).__name__}: {exc}"}]
                db.commit()
            raise
        finally:
            db.close()

    async def _fetch_all(
        self, feeds: list[FeedDefinition], health_by_feed: dict[str, FeedHealth]
    ) -> list[FeedFetchResult]:
        import random

        semaphore = asyncio.Semaphore(5)
        collector_context = (
            self.collector_factory() if self.collector_factory is not None else RSSCollector()
        )

        async with collector_context as collector:
            async def fetch(feed: FeedDefinition) -> FeedFetchResult:
                health = health_by_feed.get(feed.id)
                async with semaphore:
                    # Small jitter keeps bursts polite towards publishers that rate-limit.
                    await asyncio.sleep(random.uniform(0, 0.35))
                    return await collector.fetch_feed(
                        feed,
                        etag=health.etag if health else None,
                        last_modified=health.last_modified if health else None,
                    )

            return list(await asyncio.gather(*(fetch(feed) for feed in feeds)))

    def _record_health(self, db: Session, result: FeedFetchResult) -> None:
        health = db.get(FeedHealth, result.feed.id)
        if health is None:
            health = FeedHealth(
                feed_id=result.feed.id,
                publisher_id=result.feed.publisher_id,
                url=result.feed.url,
                category=result.feed.display_category,
            )
            db.add(health)
        now = utcnow()
        health.url = result.feed.url
        health.publisher_id = result.feed.publisher_id
        health.category = result.feed.display_category
        health.last_checked_at = now
        health.latency_ms = result.latency_ms
        health.http_status = result.http_status
        health.items_last_fetch = len(result.entries)
        if result.status == "not_modified":
            health.status = "ok"
            health.consecutive_failures = 0
            health.error = None
            health.last_success_at = now
        elif result.ok:
            health.status = "ok"
            health.consecutive_failures = 0
            health.error = None
            health.last_success_at = now
            health.total_items_fetched = (health.total_items_fetched or 0) + len(result.entries)
            if result.etag:
                health.etag = result.etag
            if result.last_modified:
                health.last_modified = result.last_modified
        else:
            health.status = "error"
            health.consecutive_failures = (health.consecutive_failures or 0) + 1
            health.error = (result.error or "unknown")[:500]
        db.flush()

    @staticmethod
    def _near_duplicate_in_batch(simhashes: dict[str, list[int]], draft: ArticleDraft) -> bool:
        target = int(draft.simhash, 16)
        return any(
            hamming_distance(target, existing) <= 3
            for existing in simhashes.get(draft.publisher_id, [])
        )

    async def _embed_and_assign(
        self,
        db: Session,
        run: IngestionRun,
        counters: RunCounters,
        bundles: list[DraftBundle],
    ) -> None:
        ordered = sorted(bundles, key=lambda bundle: bundle.draft.published_at)
        texts = [bundle.draft.embedding_text for bundle in ordered]
        vectors = await asyncio.to_thread(embedding_service.encode, texts)
        info: EmbeddingInfo = embedding_service.info
        logger.info("Embedded %s articles with %s (%sd)", len(texts), info.model, info.dim)

        event_service = EventService(db, self.config)
        event_cache: dict[int, Event] = {}

        for index, (bundle, vector) in enumerate(zip(ordered, vectors)):
            if vector is None or not np.any(vector):
                counters.items_invalid += 1
                continue
            draft = bundle.draft
            article = Article(
                publisher_id=draft.publisher_id,
                title=draft.title,
                summary=draft.summary,
                content=draft.content,
                url=draft.url,
                canonical_url=draft.canonical_url,
                url_hash=draft.url_hash,
                content_hash=draft.content_hash,
                simhash=draft.simhash,
                author=draft.author,
                image_url=draft.image_url,
                published_at=draft.published_at,
                fetched_at=utcnow(),
                category=draft.category,
                language=draft.language,
                entities=draft.entities,
                keywords=draft.keywords,
                word_count=draft.word_count,
                embedding=pack_vector(vector),
                embedding_dim=int(vector.shape[0]),
                embedding_model=info.model,
                embedding_hash=text_fingerprint(draft.embedding_text),
                is_valid=True,
            )

            savepoint = db.begin_nested()
            try:
                db.add(article)
                db.flush()

                candidates = event_service.candidate_events(draft.published_at, info.model)
                match_candidates: list[EventCandidate] = []
                for event in candidates:
                    previous = event_cache.get(event.id)
                    if previous is not None:
                        event = previous
                    centroid = unpack_vector(event.centroid, event.centroid_dim)
                    if centroid is None:
                        continue
                    match_candidates.append(
                        EventCandidate(
                            event_id=event.id,
                            centroid=centroid,
                            entities={entity.lower() for entity in (event.entities or [])},
                            keywords={keyword.lower() for keyword in (event.keywords or [])},
                            last_published_at=event.last_published_at,
                        )
                    )

                decision = choose_match(
                    embedding=vector,
                    entities=draft.entities,
                    keywords=draft.keywords,
                    published_at=draft.published_at,
                    candidates=match_candidates,
                    config=self.config,
                )

                if decision.matched and decision.event_id is not None:
                    event = event_cache.get(decision.event_id) or db.get(Event, decision.event_id)
                    if event is None:
                        decision.event_id = None
                    else:
                        event_service.assign_article(event, article, decision)
                        event_cache[event.id] = event
                        counters.events_updated += 1
                if not decision.matched:
                    event = event_service.create_event_from_article(article)
                    event_cache[event.id] = event
                    counters.events_created += 1

                counters.items_new += 1
                savepoint.commit()
            except Exception as exc:
                savepoint.rollback()
                if article in db:
                    db.expunge(article)
                logger.warning("Failed to process article '%s': %s", draft.title[:80], exc)
                counters.add_error(bundle.feed.id, f"article:{type(exc).__name__}: {exc}")

            if (index + 1) % 25 == 0:
                db.commit()
                self._persist_run(db, run, counters)
                db.commit()

        db.commit()
        self._persist_run(db, run, counters)
        db.commit()

    @staticmethod
    def _persist_run(db: Session, run: IngestionRun, counters: RunCounters) -> None:
        run.items_new = counters.items_new
        run.events_created = counters.events_created
        run.events_updated = counters.events_updated
        run.items_duplicate = counters.items_duplicate
        run.items_invalid = counters.items_invalid
        run.items_fetched = counters.items_fetched
        run.errors = counters.errors


ingestion_service = IngestionService()
