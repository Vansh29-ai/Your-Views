"""Background ingestion scheduler (single process, async).

A full production deployment would move this to a worker/queue; for a single-node deployment
an asyncio loop with a hard concurrency lock is sufficient and keeps the stack small.
"""

from __future__ import annotations

import asyncio
import logging

from app.config.settings import settings
from app.services.ingestion_service import ingestion_service

logger = logging.getLogger(__name__)


class IngestionScheduler:
    def __init__(self, interval_minutes: int | None = None, run_on_startup: bool = True) -> None:
        self.interval_seconds = max(5, (interval_minutes or settings.ingestion_interval_minutes) * 60)
        self.run_on_startup = run_on_startup
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop(), name="yourviews-ingestion-scheduler")
        logger.info("Ingestion scheduler started (every %ss)", self.interval_seconds)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # pragma: no cover - shutdown path
                pass
            self._task = None

    async def _loop(self) -> None:
        if self.run_on_startup:
            await asyncio.sleep(3)
            await self._tick("startup")
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
                return
            except asyncio.TimeoutError:
                await self._tick("scheduled")

    async def _tick(self, trigger: str) -> None:
        if ingestion_service.is_running:
            logger.debug("Skipping %s ingestion tick: run already active", trigger)
            return
        try:
            await ingestion_service.run(trigger)
        except Exception:
            logger.exception("Scheduled ingestion failed")


scheduler = IngestionScheduler()
