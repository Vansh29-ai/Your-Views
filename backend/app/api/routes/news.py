"""Article (news) endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.api.schemas import ArticleOut
from app.api.serializers import PublisherDirectory, article_detail
from app.database.models import Article

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=dict)
def list_articles(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    publisher: str | None = None,
    category: str | None = None,
    event_id: int | None = None,
) -> dict:
    statement = select(Article).where(Article.is_valid.is_(True))
    if publisher:
        statement = statement.where(Article.publisher_id == publisher)
    if category:
        statement = statement.where(Article.category == category)
    if event_id:
        statement = statement.where(Article.event_id == event_id)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(
        statement.order_by(Article.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    directory = PublisherDirectory(db)
    return {
        "items": [article_detail(article, directory, include_content=False) for article in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: DbSession) -> ArticleOut:
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    directory = PublisherDirectory(db)
    return ArticleOut(**article_detail(article, directory))
