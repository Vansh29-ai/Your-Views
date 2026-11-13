"""YOUR VIEWS — application configuration.

All tunable behaviour (ML thresholds, ingestion cadence, database URL) lives here and
is overridable through environment variables / a .env file.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
SOURCES_FILE = Path(__file__).resolve().parent / "sources.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        env_prefix="YV_",
        extra="ignore",
    )

    # ---- app ----
    app_name: str = "YOUR VIEWS"
    api_prefix: str = "/api"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ]
    )

    # ---- storage ----
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'yourviews.db').as_posix()}"

    # ---- ingestion ----
    request_timeout_seconds: float = 30.0
    request_retries: int = 2
    max_articles_per_feed: int = 40
    ingestion_interval_minutes: int = 30
    enable_scheduler: bool = True
    ingest_on_startup: bool = True
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 YourViews/1.0 (+news-aggregation; contact: local)"
    )

    # ---- NLP / ML ----
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    allow_embedding_fallback: bool = True
    embedding_batch_size: int = 32
    # Minimum cosine similarity for a strong semantic match with an event centroid.
    # Calibrated on live cross-publisher coverage: same-event pairs cluster at 0.70-0.95,
    # topic-adjacent-but-different pairs sit around 0.55-0.68.
    strong_similarity: float = 0.70
    # Weaker similarity accepted when entity / keyword evidence corroborates it.
    weak_similarity: float = 0.58
    # Candidate events considered for incremental matching.
    candidate_window_hours: int = 96
    candidate_limit: int = 60
    # Event matching composite weights (normalised at runtime).
    weight_similarity: float = 0.62
    weight_entities: float = 0.22
    weight_keywords: float = 0.10
    weight_time: float = 0.06
    # Batch clustering.
    cluster_min_samples: int = 2
    cluster_eps: float = 0.38
    cluster_time_window_hours: int = 72
    # Event lifecycle.
    min_event_publishers: int = 1
    event_title_max_chars: int = 140
    event_summary_max_chars: int = 320

    # ---- ingestion scheduler / ops ----
    enable_ingest_api_key: bool = False
    ingest_api_key: str | None = None
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
