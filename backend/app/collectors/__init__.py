"""Collector package: RSS-first ingestion plus a licensed-API extension point."""

from app.collectors.source_manager import FeedDefinition, PublisherDefinition, SourceManager, source_manager

__all__ = ["FeedDefinition", "PublisherDefinition", "SourceManager", "source_manager"]
