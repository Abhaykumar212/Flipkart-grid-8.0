from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.causes import RootCause
from backend.llm import LLMClient, client_from_config
from backend.storage.models import ProductReviewSummary

from .retrieve import retrieve_reviews
from .summarize import summarize_reviews


SUMMARY_VERSION = "review-summary-v1"


def _to_dict(row: ProductReviewSummary) -> dict[str, object]:
    return {
        "product_id": row.product_id,
        "summary_version": row.summary_version,
        "pros": row.pros,
        "cons": row.cons,
        "themes": row.themes,
        "sentiment_score": row.sentiment_score,
        "source_review_ids": row.source_review_ids,
        "generated_by": row.generated_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def get_summary(
    db: Session,
    product_id: str,
    *,
    summary_version: str = SUMMARY_VERSION,
) -> dict[str, object] | None:
    row = db.scalar(select(ProductReviewSummary).where(
        ProductReviewSummary.product_id == product_id,
        ProductReviewSummary.summary_version == summary_version,
    ))
    return _to_dict(row) if row else None


def summary_available(db: Session, product_ids: tuple[str, ...] | list[str]) -> bool:
    identifiers = tuple(dict.fromkeys(product_ids))
    if not identifiers:
        return False
    return db.scalar(select(ProductReviewSummary.summary_id).where(
        ProductReviewSummary.product_id.in_(identifiers),
        ProductReviewSummary.summary_version == SUMMARY_VERSION,
    ).limit(1)) is not None


def get_or_create_summary(
    db: Session,
    product_id: str,
    *,
    client: LLMClient | None = None,
    summary_version: str = SUMMARY_VERSION,
) -> dict[str, object] | None:
    existing = get_summary(db, product_id, summary_version=summary_version)
    if existing is not None:
        return existing
    reviews = retrieve_reviews(db, product_id, RootCause.PRODUCT_QUALITY_UNCERTAINTY)
    if not reviews:
        return None
    summary = summarize_reviews(reviews, client=client or client_from_config())
    row = ProductReviewSummary(
        summary_id=f"RS-{uuid4().hex}",
        product_id=product_id,
        summary_version=summary_version,
        pros=list(summary.pros),
        cons=list(summary.cons),
        themes=list(summary.themes),
        sentiment_score=summary.sentiment_score,
        source_review_ids=list(summary.source_review_ids),
        generated_by=summary.generated_by,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return _to_dict(row)
