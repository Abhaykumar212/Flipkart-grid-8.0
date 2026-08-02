from __future__ import annotations

from sqlalchemy import select

from backend.review_intelligence.cache import get_or_create_summary
from backend.storage.db import SessionLocal
from backend.storage.models import Product


def warm() -> int:
    with SessionLocal() as db, db.begin():
        product_ids = tuple(db.scalars(select(Product.product_id).order_by(Product.product_id)))
        return sum(get_or_create_summary(db, product_id) is not None for product_id in product_ids)


if __name__ == "__main__":
    print(f"Warmed {warm()} grounded review summaries.")

