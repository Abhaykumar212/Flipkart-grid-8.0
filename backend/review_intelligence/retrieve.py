from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.causes import RootCause
from backend.storage.models import ProductReview


CONCERN_QUERIES = {
    RootCause.PRODUCT_QUALITY_UNCERTAINTY: "quality durability build defect performance battery camera",
    RootCause.TRUST_OR_RETURN_POLICY_CONCERN: "trust return replacement warranty seller authentic",
    RootCause.PRICE_SENSITIVITY: "price value cost discount expensive worth",
    RootCause.DELIVERY_CONCERN: "delivery packaging damaged late shipping",
}


@dataclass(frozen=True, slots=True)
class RetrievedReview:
    review_id: str
    product_id: str
    rating: int
    title: str
    body: str
    helpful_count: int
    sentiment: str
    themes: tuple[str, ...]
    relevance: float

    @property
    def text(self) -> str:
        return f"{self.title}. {self.body}".strip()


def _as_retrieved(review: ProductReview, relevance: float) -> RetrievedReview:
    return RetrievedReview(
        review_id=review.review_id,
        product_id=review.product_id,
        rating=review.rating,
        title=review.title,
        body=review.body,
        helpful_count=review.helpful_count,
        sentiment=review.sentiment,
        themes=tuple(review.themes or ()),
        relevance=round(float(relevance), 6),
    )


def retrieve_reviews(
    db: Session,
    product_id: str,
    cause: RootCause = RootCause.PRODUCT_QUALITY_UNCERTAINTY,
    *,
    limit: int = 8,
) -> tuple[RetrievedReview, ...]:
    reviews = list(db.scalars(
        select(ProductReview)
        .where(ProductReview.product_id == product_id)
        .order_by(ProductReview.review_id)
    ))
    if not reviews or limit <= 0:
        return ()
    documents = [f"{item.title} {item.body} {' '.join(item.themes or [])}" for item in reviews]
    query = CONCERN_QUERIES.get(cause, CONCERN_QUERIES[RootCause.PRODUCT_QUALITY_UNCERTAINTY])
    matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform([*documents, query])
    scores = cosine_similarity(matrix[:-1], matrix[-1]).ravel()
    ranked_indices = sorted(
        range(len(reviews)),
        key=lambda index: (-scores[index], -reviews[index].helpful_count, reviews[index].review_id),
    )
    selected = ranked_indices[:limit]
    negative_indices = [
        index
        for index in ranked_indices
        if reviews[index].rating <= 2 or reviews[index].sentiment == "NEGATIVE"
    ][:2]
    for index in negative_indices:
        if index not in selected:
            selected[-1] = index
    selected = list(dict.fromkeys(selected))
    if len(selected) < min(limit, len(reviews)):
        selected.extend(index for index in ranked_indices if index not in selected)
    return tuple(_as_retrieved(reviews[index], scores[index]) for index in selected[:limit])

