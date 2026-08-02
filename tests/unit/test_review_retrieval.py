from types import SimpleNamespace

from backend.domain.causes import RootCause
from backend.review_intelligence.retrieve import retrieve_reviews


class FakeSession:
    def __init__(self, reviews):
        self.reviews = reviews

    def scalars(self, _statement):
        return iter(self.reviews)


def _review(identifier, rating, title, body, helpful):
    return SimpleNamespace(
        review_id=identifier,
        product_id="p1",
        rating=rating,
        title=title,
        body=body,
        helpful_count=helpful,
        sentiment="NEGATIVE" if rating <= 2 else "POSITIVE",
        themes=[],
    )


def test_tfidf_retrieval_is_relevant_and_includes_available_negatives():
    reviews = [
        _review("r1", 5, "Excellent camera", "sharp camera quality", 8),
        _review("r2", 5, "Good value", "low price", 10),
        _review("r3", 1, "Build defect", "poor durability defect", 2),
        _review("r4", 2, "Battery issue", "battery performance is weak", 1),
    ]
    result = retrieve_reviews(FakeSession(reviews), "p1", RootCause.PRODUCT_QUALITY_UNCERTAINTY, limit=3)
    assert len(result) == 3
    assert sum(item.rating <= 2 for item in result) == 2
    assert result[0].relevance >= result[-1].relevance or result[-1].rating <= 2

