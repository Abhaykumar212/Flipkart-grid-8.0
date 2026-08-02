from time import perf_counter

from sqlalchemy import func, select

from backend.review_intelligence.cache import get_or_create_summary, get_summary
from backend.storage.models import Product, ProductReview, ProductReviewSummary


def test_all_products_can_be_warmed_and_cache_is_grounded(api_harness):
    with api_harness.sessions() as db, db.begin():
        product_ids = tuple(db.scalars(select(Product.product_id)))
        for product_id in product_ids:
            assert get_or_create_summary(db, product_id) is not None
        assert db.scalar(select(func.count()).select_from(ProductReviewSummary)) == 50
        valid_ids_by_product: dict[str, set[str]] = {}
        for review_id, product_id in db.execute(
            select(ProductReview.review_id, ProductReview.product_id)
        ):
            valid_ids_by_product.setdefault(product_id, set()).add(review_id)
        summaries = tuple(db.scalars(select(ProductReviewSummary)))
        assert all(
            set(item.source_review_ids).issubset(valid_ids_by_product[item.product_id])
            for item in summaries
        )
        started = perf_counter()
        assert get_summary(db, product_ids[0]) is not None
        assert (perf_counter() - started) * 1_000 < 10


def test_review_summary_api_discloses_grounding(api_harness):
    response = api_harness.client.get("/api/v1/products/p-1001/review-summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pros"] and payload["cons"]
    assert payload["source_review_ids"]
    assert payload["generated_by"] in {"LLM", "TEMPLATE"}
