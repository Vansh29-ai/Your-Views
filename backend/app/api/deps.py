"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.connection import get_db
from app.services.event_service import EventService

DbSession = Annotated[Session, Depends(get_db)]


def event_service(db: DbSession) -> EventService:
    return EventService(db, settings)


EventServiceDep = Annotated[EventService, Depends(event_service)]


def require_admin_key(x_api_key: str | None = Header(default=None)) -> None:
    """Optional hardening: enable with YV_ENABLE_INGEST_API_KEY=true."""
    if not settings.enable_ingest_api_key:
        return
    if not settings.ingest_api_key or x_api_key != settings.ingest_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
