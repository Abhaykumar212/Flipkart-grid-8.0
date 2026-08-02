from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.session_state.state import SessionState

from .schema import FEATURE_SCHEMA_V1, ProductFacts, UserHistory, clamp_feature


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return _aware(value)
    if not isinstance(value, str):
        return None
    try:
        return _aware(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def _elapsed_seconds(later: datetime, earlier: datetime | None) -> float:
    if earlier is None:
        return 0.0
    return max(0.0, (_aware(later) - _aware(earlier)).total_seconds())


def _cart_products(
    state: SessionState,
    history: UserHistory,
) -> list[tuple[dict[str, Any], ProductFacts]]:
    products: list[tuple[dict[str, Any], ProductFacts]] = []
    for item in state.cart.get("items", []):
        product = history.products.get(str(item.get("product_id", "")))
        if product is not None and int(item.get("quantity", 0)) > 0:
            products.append((item, product))
    return products


def _delivery_observations(state: SessionState) -> list[float]:
    observations: list[float] = []
    for event in state.recent_events:
        if event.get("event_type") != "DELIVERY_CHECKED":
            continue
        metadata = event.get("metadata") or {}
        if metadata.get("available", True):
            observations.append(float(metadata.get("estimated_days", 5)))
    return observations


def _event_count(state: SessionState) -> int:
    """Recover total count from the gapless sequence even though only 50 are cached."""

    sequence_numbers = [
        int(event.get("sequence_no", 0))
        for event in state.recent_events
        if event.get("sequence_no") is not None
    ]
    return max(sequence_numbers, default=len(state.recent_events))


def compute_features(
    state: SessionState,
    history: UserHistory,
) -> dict[str, float]:
    """Compute the sole canonical 67-feature vector from §9.2.

    Serving, simulation, and training all call this function (DEC-026). Raw
    values are assembled first, then emitted once in schema order and clamped
    against that contract. No caller can accidentally reorder the vector.
    """

    now = _aware(history.as_of)
    cart_items = _cart_products(state, history)
    cart_has_items = int(state.cart.get("item_count", 0)) > 0
    cart_value = float(state.cart.get("value", 0.0)) if cart_has_items else 0.0
    item_count = int(state.cart.get("item_count", 0)) if cart_has_items else 0

    categories = {product.category for _, product in cart_items}
    category_quantities: dict[str, int] = {}
    for item, product in cart_items:
        category_quantities[product.category] = (
            category_quantities.get(product.category, 0) + int(item["quantity"])
        )
    dominant_category = (
        min(
            category_quantities,
            key=lambda category: (-category_quantities[category], category),
        )
        if category_quantities
        else None
    )
    historical_category_total = sum(history.category_order_counts.values())
    category_affinity = (
        history.category_order_counts.get(dominant_category, 0)
        / historical_category_total
        if dominant_category is not None and historical_category_total > 0
        else 0.0
    )

    # §9.2 Group 1: all-time user aggregates and cold-start priors.
    raw: dict[str, float | int | bool] = {
        "u_lifetime_orders": history.lifetime_orders,
        "u_prior_abandonment_rate": history.prior_abandonment_rate,
        "u_avg_order_value": history.avg_order_value,
        "u_discount_usage_rate": history.discount_usage_rate,
        "u_category_affinity": category_affinity,
        "u_days_since_last_purchase": history.days_since_last_purchase,
        "u_avg_session_to_purchase_s": history.avg_session_to_purchase_s,
        "u_return_rate": history.return_rate,
        "u_is_new_user": history.lifetime_orders == 0,
        "u_affinity_informational": history.affinity_informational,
        "u_affinity_incentive": history.affinity_incentive,
    }

    # §9.2 Group 2: active-cart value, friction, age, and price movement.
    catalog_mrp_total = sum(
        int(item["quantity"]) * product.mrp for item, product in cart_items
    )
    mrp_total = float(state.cart.get("mrp_total", 0.0)) or catalog_mrp_total
    first_add_at = _timestamp(state.cart.get("first_add_at"))
    price_drops: list[float] = []
    price_increased = False
    for _, product in cart_items:
        if not product.price_history:
            continue
        # The catalogue's first observed price is the immutable first-view
        # proxy available in the Phase 4 event contract.
        first_price = product.price_history[0]
        if first_price > 0:
            price_drops.append((first_price - product.selling_price) / first_price * 100)
            price_increased = price_increased or product.selling_price > first_price
    raw.update({
        "c_value": cart_value,
        "c_item_count": item_count,
        "c_distinct_categories": len(categories) if cart_has_items else 0,
        "c_value_to_aov_ratio": (
            cart_value / history.avg_order_value
            if cart_has_items and history.avg_order_value > 0
            else 0.0
        ),
        "c_discount_pct_available": (
            max(0.0, (mrp_total - cart_value) / mrp_total * 100)
            if cart_has_items and mrp_total > 0
            else 0.0
        ),
        "c_age_seconds": _elapsed_seconds(now, first_add_at) if cart_has_items else 0.0,
        "c_promo_applied": bool(state.cart.get("promo_code")) if cart_has_items else False,
        "c_max_price_drop_pct": max(price_drops, default=0.0) if cart_has_items else 0.0,
        "c_price_increased_since_view": price_increased if cart_has_items else False,
    })

    # §9.2 Group 3: quantity-weighted catalogue quality and availability.
    weighted_quantity = sum(int(item["quantity"]) for item, _ in cart_items)
    raw.update({
        "p_max_item_price": max(
            (float(item.get("unit_price", product.selling_price)) for item, product in cart_items),
            default=0.0,
        ),
        "p_avg_rating": (
            sum(product.rating * int(item["quantity"]) for item, product in cart_items)
            / weighted_quantity
            if weighted_quantity > 0
            else 4.0
        ),
        "p_min_rating_count": min(
            (product.rating_count for _, product in cart_items), default=0
        ),
        "p_any_low_stock": any(product.quantity_left <= 5 for _, product in cart_items),
        "p_any_out_of_stock": any(not product.in_stock for _, product in cart_items),
    })

    # §9.2 Group 4: current delivery facts plus session delivery checks.
    delivery_days = _delivery_observations(state) or [
        float(product.estimated_delivery_days) for _, product in cart_items
    ]
    delivery_fee = float(state.cart.get("delivery_fee", 0.0)) if cart_has_items else 0.0
    raw.update({
        "d_max_days": max(delivery_days, default=5.0),
        "d_min_days": min(delivery_days, default=5.0),
        "d_fee": delivery_fee,
        "d_fee_pct_of_cart": (
            delivery_fee / cart_value * 100 if cart_value > 0 else 0.0
        ),
        "d_check_count": state.counters.get("delivery_checks", 0),
    })

    # §9.2 Group 5: payment history, failures, method changes, EMI, funnel depth.
    raw.update({
        "pay_method_on_file": history.payment_method_on_file,
        "pay_failure_count": state.counters.get("payment_failures", 0),
        "pay_method_change_count": state.counters.get("payment_method_changes", 0),
        "pay_emi_eligible": any(product.emi_eligible for _, product in cart_items),
        "pay_checkout_max_step": state.counters.get("checkout_max_step", 0),
    })

    # §9.2 Group 6: session-window behavior and current activity rate.
    duration_seconds = _elapsed_seconds(now, _aware(state.started_at))
    idle_seconds = _elapsed_seconds(now, state.last_event_at)
    event_count = _event_count(state)
    event_velocity = event_count / max(duration_seconds / 60.0, 1.0)
    cart_adds = state.counters.get("cart_adds", 0)
    cart_removes = state.counters.get("cart_removes", 0)
    raw.update({
        "s_duration_seconds": duration_seconds,
        "s_product_view_count": state.counters.get("product_views", 0),
        "s_distinct_products_viewed": state.counters.get("distinct_products_viewed", 0),
        "s_review_open_count": state.counters.get("review_opens", 0),
        "s_review_dwell_seconds": state.counters.get("review_dwell_ms", 0) / 1_000,
        "s_similar_product_view_count": state.counters.get("similar_product_views", 0),
        "s_comparison_count": state.counters.get("comparisons", 0),
        "s_cart_view_count": state.counters.get("cart_views", 0),
        "s_cart_add_count": cart_adds,
        "s_cart_remove_count": cart_removes,
        "s_cart_product_switch_count": max(0, cart_adds + cart_removes - item_count),
        "s_search_count": state.counters.get("searches", 0),
        "s_price_sort_count": state.counters.get("price_sorts", 0),
        "s_coupon_search_count": state.counters.get("coupon_searches", 0),
        "s_checkout_start_count": state.counters.get("checkout_starts", 0),
        "s_back_from_checkout_count": state.counters.get("back_from_checkout", 0),
        "s_idle_seconds_current": idle_seconds,
        "s_event_velocity_per_min": event_velocity,
    })

    # §9.2 Group 7: immutable session context and exhaustive referral one-hot.
    session_time = _aware(state.started_at)
    referral = (state.referral_source or "DIRECT").upper()
    referral_bucket = referral if referral in {"DIRECT", "SEARCH", "SOCIAL", "EMAIL"} else "DIRECT"
    raw.update({
        "x_is_mobile": (state.device_type or "").upper() == "MOBILE",
        "x_hour_of_day": session_time.hour,
        "x_is_late_night": session_time.hour >= 23 or session_time.hour < 5,
        "x_is_weekend": session_time.weekday() >= 5,
        "x_is_returning_user": state.is_returning_user or history.lifetime_orders > 0,
        "x_referral_direct": referral_bucket == "DIRECT",
        "x_referral_search": referral_bucket == "SEARCH",
        "x_referral_social": referral_bucket == "SOCIAL",
        "x_referral_email": referral_bucket == "EMAIL",
    })

    # §9.2 Group 8: post-treatment history, kept out of RISK_MODEL_FEATURES.
    shown = state.interventions.get("shown", [])
    last_shown_at = _timestamp(state.interventions.get("last_shown_at"))
    raw.update({
        "i_shown_count": len(shown),
        "i_dismissal_count": state.interventions.get("dismissal_count", 0),
        "i_click_count": state.interventions.get("click_count", 0),
        "i_seconds_since_last": (
            _elapsed_seconds(now, last_shown_at) if last_shown_at else 3_600.0
        ),
        "i_distinct_types_shown": len({
            item.get("intervention_id") for item in shown if item.get("intervention_id")
        }),
    })

    return {
        spec.name: clamp_feature(spec.name, raw.get(spec.name, spec.default))
        for spec in FEATURE_SCHEMA_V1
    }
