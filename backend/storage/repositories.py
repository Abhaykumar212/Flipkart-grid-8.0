from collections import Counter
from datetime import datetime, timezone
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.enums import CostLevel
from backend.feedback.affinity import affinity_for_family
from backend.feature_engine.schema import ProductFacts, UserHistory

from .models import (
    DecisionTrace,
    InterventionCatalogue,
    InterventionOutcome,
    Order,
    Product,
    ProductReview,
    ShoppingSession,
    User,
)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _catalogue_facts(session: Session) -> dict[str, ProductFacts]:
    facts: dict[str, ProductFacts] = {}
    for product in session.scalars(select(Product).order_by(Product.product_id)):
        prices: list[float] = []
        for point in product.price_history or []:
            try:
                prices.append(float(point["price"]))
            except (KeyError, TypeError, ValueError):
                continue
        facts[product.product_id] = ProductFacts(
            product_id=product.product_id,
            category=product.category,
            mrp=float(product.mrp),
            selling_price=float(product.selling_price),
            rating=float(product.rating_value),
            rating_count=int(product.rating_count),
            in_stock=bool(product.in_stock),
            quantity_left=int(product.quantity_left),
            estimated_delivery_days=int(product.estimated_delivery_days),
            emi_eligible=product.emi_monthly is not None and product.emi_months is not None,
            price_history=tuple(prices),
        )
    return facts


def _order_category_counts(
    orders: list[Order],
    products: dict[str, ProductFacts],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for order in orders:
        for item in order.items or []:
            if not isinstance(item, dict):
                continue
            product = products.get(str(item.get("product_id") or item.get("id") or ""))
            category = item.get("category") or (product.category if product else None)
            if category:
                counts[str(category)] += max(1, int(item.get("quantity", 1)))
    return counts


def user_history(
    session: Session,
    user_id: str | None,
    *,
    as_of: datetime | None = None,
) -> UserHistory:
    """Return leakage-aware historical aggregates with cold-start defaults.

    Abandonment and discount rates use Laplace smoothing; intervention CTRs use
    Beta(1, 1) smoothing. Unknown/anonymous users receive the §9.2 priors while
    still receiving the product catalogue needed to describe their live cart.
    """

    observed_at = _aware(as_of or datetime.now(timezone.utc))
    products = _catalogue_facts(session)
    if not user_id:
        return UserHistory(as_of=observed_at, products=products)

    user = session.get(User, user_id)
    if user is None:
        return UserHistory(as_of=observed_at, products=products)

    orders = list(session.scalars(
        select(Order).where(Order.user_id == user_id).order_by(Order.placed_at)
    ))
    historical_sessions = list(session.scalars(
        select(ShoppingSession)
        .where(
            ShoppingSession.user_id == user_id,
            ShoppingSession.outcome.in_(("ABANDONED", "CONVERTED")),
        )
        .order_by(ShoppingSession.started_at)
    ))

    abandoned = sum(item.outcome == "ABANDONED" for item in historical_sessions)
    prior_abandonment_rate = (
        (abandoned + 1) / (len(historical_sessions) + 2)
        if historical_sessions
        else (
            float(user.prior_abandonment_rate)
            if user.prior_abandonment_rate is not None
            else 0.5
        )
    )

    converted_durations = [
        max(
            0.0,
            (_aware(item.outcome_resolved_at) - _aware(item.started_at)).total_seconds(),
        )
        for item in historical_sessions
        if item.outcome == "CONVERTED" and item.outcome_resolved_at is not None
    ]
    average_purchase_seconds = mean(converted_durations) if converted_durations else 900.0

    actual_order_count = len(orders)
    lifetime_orders = max(int(user.lifetime_orders or 0), actual_order_count)
    average_order_value = (
        mean(float(order.order_value) for order in orders)
        if orders
        else (float(user.avg_order_value) if user.avg_order_value else 15_000.0)
    )
    discount_usage_rate = (
        (sum(float(order.discount_applied) > 0 for order in orders) + 1)
        / (actual_order_count + 2)
        if orders
        else (
            float(user.discount_usage_rate)
            if user.discount_usage_rate is not None
            else 0.3
        )
    )

    last_purchase_candidates = [order.placed_at for order in orders]
    if user.last_purchase_at is not None:
        last_purchase_candidates.append(user.last_purchase_at)
    days_since_last_purchase = (
        max(
            0.0,
            (observed_at - max(_aware(value) for value in last_purchase_candidates))
            .total_seconds()
            / 86_400,
        )
        if last_purchase_candidates
        else 365.0
    )

    affinity_rows = [
        (str(cost), bool(clicked))
        for cost, clicked in session.execute(
            select(InterventionCatalogue.cost_level, InterventionOutcome.clicked)
            .join(
                DecisionTrace,
                InterventionOutcome.decision_id == DecisionTrace.decision_id,
            )
            .join(
                ShoppingSession,
                ShoppingSession.session_id == DecisionTrace.session_id,
            )
            .join(
                InterventionCatalogue,
                InterventionCatalogue.intervention_id
                == DecisionTrace.selected_intervention,
            )
            .where(
                ShoppingSession.user_id == user_id,
                InterventionOutcome.intervention_shown.is_(True),
            )
        )
    ]

    return UserHistory(
        as_of=observed_at,
        lifetime_orders=lifetime_orders,
        prior_abandonment_rate=prior_abandonment_rate,
        avg_order_value=average_order_value,
        discount_usage_rate=discount_usage_rate,
        category_order_counts=dict(_order_category_counts(orders, products)),
        days_since_last_purchase=days_since_last_purchase,
        avg_session_to_purchase_s=average_purchase_seconds,
        return_rate=(float(user.return_rate) if user.return_rate is not None else 0.08),
        affinity_informational=affinity_for_family(affinity_rows, CostLevel.LOW),
        affinity_incentive=affinity_for_family(affinity_rows, CostLevel.HIGH),
        payment_method_on_file=bool(orders),
        products=products,
    )


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
