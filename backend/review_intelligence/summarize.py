from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer

from backend import config
from backend.llm import LLMClient

from .retrieve import RetrievedReview
from .sanitize import delimited_review_block, sanitize_reviews


SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "pros": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "cons": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "themes": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "sentiment_score": {"type": "number", "minimum": 0, "maximum": 1},
        "source_review_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["pros", "cons", "themes", "sentiment_score", "source_review_ids"],
    "additionalProperties": False,
}


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    pros: tuple[str, ...]
    cons: tuple[str, ...]
    themes: tuple[str, ...]
    sentiment_score: float
    source_review_ids: tuple[str, ...]
    generated_by: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pros": list(self.pros),
            "cons": list(self.cons),
            "themes": list(self.themes),
            "sentiment_score": self.sentiment_score,
            "source_review_ids": list(self.source_review_ids),
            "generated_by": self.generated_by,
        }


def _bullet(review: RetrievedReview) -> str:
    return review.title.strip() or review.body.strip().split(".", maxsplit=1)[0]


def _themes(reviews: tuple[RetrievedReview, ...]) -> tuple[str, ...]:
    documents = [review.text for review in reviews]
    if not documents:
        return ()
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5)
        vectorizer.fit(documents)
        return tuple(sorted(vectorizer.get_feature_names_out().tolist()))
    except ValueError:
        return ()


def extractive_summary(reviews: tuple[RetrievedReview, ...]) -> ReviewSummary:
    if not reviews:
        raise ValueError("at least one review is required")
    helpful = sorted(reviews, key=lambda item: (-item.helpful_count, item.review_id))
    positives = [item for item in helpful if item.rating >= 4][:3]
    low_to_high = sorted(reviews, key=lambda item: (item.rating, -item.helpful_count, item.review_id))
    negatives = [item for item in low_to_high if item.rating <= 2][:3]
    negatives.extend(item for item in low_to_high if item not in negatives)
    negatives = negatives[: min(3, len(reviews))]
    source_ids = tuple(dict.fromkeys(item.review_id for item in [*positives, *negatives]))
    return ReviewSummary(
        pros=tuple(_bullet(item) for item in positives),
        cons=tuple(_bullet(item) for item in negatives),
        themes=_themes(reviews),
        sentiment_score=round((mean(item.rating for item in reviews) - 1) / 4, 6),
        source_review_ids=source_ids,
        generated_by="TEMPLATE",
    )


def summarize_reviews(
    reviews: tuple[RetrievedReview, ...],
    *,
    client: LLMClient | None = None,
) -> ReviewSummary:
    safe = sanitize_reviews(reviews)
    if not safe:
        raise ValueError("no safe reviews are available")
    fallback = extractive_summary(safe)
    if client is None:
        return fallback
    prompt = (
        "Summarize only the delimited reviews as grounded pros and cons. Return "
        "source_review_ids using the real review IDs listed below.\n\n"
        + delimited_review_block(safe)
        + "\n\nReal review IDs: "
        + ", ".join(item.review_id for item in safe)
    )
    try:
        payload = client.generate_json(prompt, SUMMARY_SCHEMA, 500, config.LLM_TIMEOUT_SECONDS)
        allowed = {item.review_id for item in safe}
        source_ids = tuple(str(item) for item in payload["source_review_ids"])
        if not source_ids or not set(source_ids).issubset(allowed):
            return fallback
        return ReviewSummary(
            pros=tuple(str(item) for item in payload["pros"][:3]),
            cons=tuple(str(item) for item in payload["cons"][:3]),
            themes=tuple(str(item) for item in payload["themes"][:5]),
            sentiment_score=max(0.0, min(1.0, float(payload["sentiment_score"]))),
            source_review_ids=source_ids,
            generated_by="LLM",
        )
    except (KeyError, TypeError, ValueError, RuntimeError):
        return fallback
