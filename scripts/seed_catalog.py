"""Idempotently seed products, reviews, and the governed intervention catalogue."""

from datetime import datetime
import json
from pathlib import Path

from backend.recommendation.catalogue import INTERVENTION_CATALOGUE
from backend.storage.db import SessionLocal
from backend.storage.models import InterventionCatalogue, Product, ProductReview
from scripts.export_catalog import export_catalog

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "fixtures" / "catalog.json"


def _sentiment(rating: int) -> str:
    if rating >= 4:
        return "POSITIVE"
    if rating <= 2:
        return "NEGATIVE"
    return "NEUTRAL"


def _upsert(session, model, key: str, values: dict) -> None:
    instance = session.get(model, key)
    if instance is None:
        session.add(model(**values))
        return
    for field, value in values.items():
        setattr(instance, field, value)


def seed_catalog(*, refresh_fixture: bool = False) -> dict[str, int]:
    if refresh_fixture or not CATALOG_PATH.exists():
        export_catalog()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    with SessionLocal.begin() as session:
        for item in catalog:
            seller = item["seller"]
            signals = item.get("signals") or {}
            emi = item.get("emi") or {}
            _upsert(session, Product, item["id"], {
                "product_id": item["id"],
                "slug": item["slug"],
                "title": item["title"],
                "brand": item["brand"],
                "category": item["category"],
                "sub_category": item["subCategory"],
                "mrp": item["price"]["mrp"],
                "selling_price": item["price"]["sellingPrice"],
                "currency": item["price"]["currency"],
                "rating_value": item["rating"]["value"],
                "rating_count": item["rating"]["count"],
                "review_count": item["rating"]["reviewCount"],
                "in_stock": item["stock"]["inStock"],
                "quantity_left": item["stock"]["quantityLeft"],
                "estimated_delivery_days": item["delivery"]["estimatedDays"],
                "free_delivery": item["delivery"]["free"],
                "emi_monthly": emi.get("monthly"),
                "emi_months": emi.get("months"),
                "seller_name": seller["name"],
                "seller_rating": seller["rating"],
                "images": item["images"],
                "highlights": item["highlights"],
                "offers": item["offers"],
                "specifications": item["specifications"],
                "price_history": signals.get("priceHistory", []),
            })
            for review in item["reviews"]:
                _upsert(session, ProductReview, review["id"], {
                    "review_id": review["id"],
                    "product_id": item["id"],
                    "reviewer_name": review["reviewerName"],
                    "rating": review["rating"],
                    "title": review["title"],
                    "body": review["text"],
                    "helpful_count": review["helpfulCount"],
                    "created_at": datetime.fromisoformat(review["date"]),
                    "sentiment": _sentiment(review["rating"]),
                    "themes": [],
                })

        for definition in INTERVENTION_CATALOGUE:
            intervention_id = definition.intervention_id.value
            _upsert(session, InterventionCatalogue, intervention_id, {
                "intervention_id": intervention_id,
                "display_name": definition.display_name,
                "supported_causes": [
                    cause.value if hasattr(cause, "value") else cause
                    for cause in definition.supported_causes
                ],
                "cost_level": definition.cost_level.value,
                "intrusiveness": definition.intrusiveness,
                "cooldown_minutes": definition.cooldown_minutes,
                "allowed_channels": [channel.value for channel in definition.allowed_channels],
                "requires": list(definition.requires),
                "prior_uplift": definition.prior_uplift,
                "max_discount_pct": definition.max_discount_pct,
                "is_active": definition.is_active,
            })

    review_count = sum(len(item["reviews"]) for item in catalog)
    return {
        "products": len(catalog),
        "reviews": review_count,
        "interventions": len(INTERVENTION_CATALOGUE),
    }


def main() -> None:
    counts = seed_catalog()
    print(
        f"Seed complete: {counts['products']} products, "
        f"{counts['reviews']} reviews, {counts['interventions']} interventions"
    )


if __name__ == "__main__":
    main()
