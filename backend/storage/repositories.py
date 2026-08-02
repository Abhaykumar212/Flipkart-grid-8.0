from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Product, ProductReview


def product_to_dict(product: Product) -> dict:
    return {
        "id": product.product_id,
        "slug": product.slug,
        "title": product.title,
        "brand": product.brand,
        "category": product.category,
        "subCategory": product.sub_category,
        "images": product.images,
        "price": {
            "mrp": product.mrp,
            "sellingPrice": product.selling_price,
            "currency": product.currency,
        },
        "rating": {
            "value": product.rating_value,
            "count": product.rating_count,
            "reviewCount": product.review_count,
        },
        "delivery": {
            "free": product.free_delivery,
            "estimatedDays": product.estimated_delivery_days,
        },
        "offers": product.offers,
        "emi": (
            {"monthly": product.emi_monthly, "months": product.emi_months}
            if product.emi_monthly is not None and product.emi_months is not None
            else None
        ),
        "stock": {"inStock": product.in_stock, "quantityLeft": product.quantity_left},
        "highlights": product.highlights,
        "seller": {"name": product.seller_name, "rating": product.seller_rating},
        "specifications": product.specifications,
        "priceHistory": product.price_history,
    }


def list_products(session: Session, category: str | None = None) -> list[dict]:
    statement = select(Product).order_by(Product.product_id)
    if category:
        statement = statement.where(Product.category == category)
    return [product_to_dict(product) for product in session.scalars(statement)]


def get_product_by_slug(session: Session, slug: str) -> dict | None:
    product = session.scalar(select(Product).where(Product.slug == slug))
    if product is None:
        return None
    result = product_to_dict(product)
    reviews = session.scalars(
        select(ProductReview)
        .where(ProductReview.product_id == product.product_id)
        .order_by(ProductReview.helpful_count.desc(), ProductReview.created_at.desc())
    )
    result["reviews"] = [
        {
            "id": review.review_id,
            "reviewerName": review.reviewer_name,
            "rating": review.rating,
            "title": review.title,
            "text": review.body,
            "helpfulCount": review.helpful_count,
            "date": review.created_at.date().isoformat(),
            "sentiment": review.sentiment,
            "themes": review.themes,
        }
        for review in reviews
    ]
    return result
