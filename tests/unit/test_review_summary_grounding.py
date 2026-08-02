from backend.review_intelligence.retrieve import RetrievedReview
from backend.review_intelligence.summarize import extractive_summary, summarize_reviews


def _reviews():
    return tuple(
        RetrievedReview(
            review_id=f"r{index}", product_id="p1", rating=rating,
            title=title, body=body, helpful_count=10 - index,
            sentiment="NEGATIVE" if rating <= 2 else "POSITIVE",
            themes=(), relevance=0.5,
        )
        for index, (rating, title, body) in enumerate([
            (5, "Strong build", "Feels durable"),
            (4, "Bright display", "Works outdoors"),
            (5, "Fast", "Performance is smooth"),
            (2, "Warm", "Gets warm under load"),
        ], start=1)
    )


class UngroundedClient:
    def generate_json(self, prompt, schema, max_tokens, timeout):
        del prompt, schema, max_tokens, timeout
        return {"pros": ["Great"], "cons": ["None"], "themes": ["quality"], "sentiment_score": 1, "source_review_ids": ["invented"]}


def test_extractive_fallback_is_valid_and_grounded():
    reviews = _reviews()
    summary = extractive_summary(reviews)
    assert len(summary.pros) == 3
    assert len(summary.cons) >= 2
    assert set(summary.source_review_ids).issubset({item.review_id for item in reviews})


def test_ungrounded_llm_summary_is_discarded():
    reviews = _reviews()
    summary = summarize_reviews(reviews, client=UngroundedClient())
    assert summary.generated_by == "TEMPLATE"
    assert set(summary.source_review_ids).issubset({item.review_id for item in reviews})

