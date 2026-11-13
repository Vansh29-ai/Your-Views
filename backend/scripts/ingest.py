#!/usr/bin/env python
"""Run one ingestion cycle from the command line.

Usage (from backend/):
    ..\\.venv\\Scripts\\python.exe scripts\\ingest.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database.init_db import init_db  # noqa: E402
from app.services.ingestion_service import ingestion_service  # noqa: E402


async def main() -> None:
    init_db()
    run_id = await ingestion_service.run("cli")
    print(f"Ingestion run {run_id} complete")


if __name__ == "__main__":
    asyncio.run(main())
