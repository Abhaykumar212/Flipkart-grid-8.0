import json
import random
from time import perf_counter
from datetime import datetime, timedelta, timezone

import pytest

from backend.feature_engine.compute import compute_features
from backend.feature_engine.schema import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_V1,
    FEATURE_SCHEMA_VERSION,
    RISK_MODEL_FEATURES,
    ProductFacts,
    UserHistory,
    serialize_feature_schema,
)
from backend.session_state.state import COUNTER_DEFAULTS, SessionState


NOW = datetime(2026, 8, 2, 23, 10, tzinfo=timezone.utc)


def _product(
    product_id: str = "p1",
    *,
    category: str = "electronics",
    mrp: float = 1_200,
    selling_price: float = 1_000,
    rating: float = 4.5,
    rating_count: int = 100,
    in_stock: bool = True,
    quantity_left: int = 3,
    delivery_days: int = 7,
    emi_eligible: bool = True,
    price_history: tuple[float, ...] = (1_100,),
) -> ProductFacts:
    return ProductFacts(
        product_id=product_id,
        category=category,
        mrp=mrp,
        selling_price=selling_price,
        rating=rating,
        rating_count=rating_count,
        in_stock=in_stock,
        quantity_left=quantity_left,
        estimated_delivery_days=delivery_days,
        emi_eligible=emi_eligible,
        price_history=price_history,
    )


def test_schema_is_ordered_versioned_serializable_and_risk_safe():
    document = json.loads(serialize_feature_schema())

    assert len(FEATURE_SCHEMA_V1) == 67
    assert len(FEATURE_NAMES) == 67
    assert document["feature_schema_version"] == FEATURE_SCHEMA_VERSION == "fs-v1"
    assert [item["name"] for item in document["features"]] == list(FEATURE_NAMES)
    assert tuple(document["risk_model_features"]) == RISK_MODEL_FEATURES
    assert len(RISK_MODEL_FEATURES) == 62
    assert not any(name.startswith("i_") for name in RISK_MODEL_FEATURES)


def test_empty_session_uses_documented_defaults_and_zero_cart_features():
    state = SessionState(session_id="empty", started_at=NOW)

    features = compute_features(state, UserHistory(as_of=NOW))

    assert tuple(features) == FEATURE_NAMES
    assert len(features) == 67
    assert all(value == 0 for name, value in features.items() if name.startswith("c_"))
    assert features["u_prior_abandonment_rate"] == 0.5
    assert features["u_avg_order_value"] == 15_000
    assert features["u_days_since_last_purchase"] == 365
    assert features["p_avg_rating"] == 4
    assert features["d_max_days"] == features["d_min_days"] == 5
    assert features["i_seconds_since_last"] == 3_600
    assert sum(features[name] for name in FEATURE_NAMES if name.startswith("x_referral_")) == 1


def test_hand_built_session_matches_representative_feature_calculations():
    state = SessionState(
        session_id="hand-built",
        started_at=NOW - timedelta(minutes=10),
        last_event_at=NOW - timedelta(seconds=30),
        device_type="MOBILE",
        referral_source="SOCIAL",
        is_returning_user=True,
    )
    state.cart.update({
        "value": 2_000,
        "mrp_total": 2_600,
        "item_count": 3,
        "delivery_fee": 100,
        "promo_code": "SAVE",
        "first_add_at": (NOW - timedelta(minutes=10)).isoformat(),
        "items": [
            {"product_id": "p1", "quantity": 1, "unit_price": 1_000},
            {"product_id": "p2", "quantity": 2, "unit_price": 500},
        ],
    })
    state.counters.update({
        "product_views": 6,
        "distinct_products_viewed": 4,
        "review_opens": 3,
        "review_dwell_ms": 45_000,
        "cart_adds": 4,
        "cart_removes": 2,
        "delivery_checks": 2,
        "payment_failures": 1,
        "checkout_max_step": 2,
    })
    state.recent_events = [{"sequence_no": 12, "event_type": "CART_VIEWED"}]
    state.interventions = {
        "shown": [
            {"intervention_id": "REVIEW_SUMMARY"},
            {"intervention_id": "PRICE_DROP_ALERT"},
        ],
        "dismissal_count": 1,
        "click_count": 1,
        "last_shown_at": (NOW - timedelta(seconds=120)).isoformat(),
    }
    history = UserHistory(
        as_of=NOW,
        lifetime_orders=3,
        avg_order_value=1_000,
        category_order_counts={"electronics": 3, "books": 1},
        payment_method_on_file=True,
        products={
            "p1": _product(),
            "p2": _product(
                "p2",
                category="books",
                mrp=700,
                selling_price=500,
                rating=3.5,
                rating_count=50,
                in_stock=False,
                quantity_left=0,
                delivery_days=3,
                emi_eligible=False,
                price_history=(400,),
            ),
        },
    )

    features = compute_features(state, history)

    assert features["u_category_affinity"] == pytest.approx(0.25)
    assert features["c_value_to_aov_ratio"] == pytest.approx(2.0)
    assert features["c_discount_pct_available"] == pytest.approx(23.076923)
    assert features["c_age_seconds"] == pytest.approx(600)
    assert features["c_max_price_drop_pct"] == pytest.approx(100 / 11)
    assert features["c_price_increased_since_view"] == 1
    assert features["p_avg_rating"] == pytest.approx((4.5 + 3.5 * 2) / 3)
    assert features["p_any_out_of_stock"] == 1
    assert features["d_fee_pct_of_cart"] == pytest.approx(5)
    assert features["pay_emi_eligible"] == 1
    assert features["s_cart_product_switch_count"] == 3
    assert features["s_event_velocity_per_min"] == pytest.approx(1.2)
    assert features["x_is_late_night"] == 1
    assert features["x_referral_social"] == 1
    assert features["i_seconds_since_last"] == pytest.approx(120)
    assert features["i_distinct_types_shown"] == 2


def test_random_states_stay_within_all_bounds_and_compute_under_budget():
    rng = random.Random(8_000)
    product = _product()
    timings_ms: list[float] = []

    for index in range(1_000):
        state = SessionState(
            session_id=f"random-{index}",
            started_at=NOW - timedelta(seconds=rng.uniform(-1_000, 10_000)),
            last_event_at=NOW - timedelta(seconds=rng.uniform(-100, 2_000)),
            device_type=rng.choice(("MOBILE", "DESKTOP", "UNKNOWN")),
            referral_source=rng.choice(("DIRECT", "SEARCH", "SOCIAL", "EMAIL", "OTHER")),
            is_returning_user=rng.choice((True, False)),
        )
        quantity = rng.randint(0, 50)
        state.cart.update({
            "value": rng.uniform(-10_000, 5_000_000),
            "mrp_total": rng.uniform(-10_000, 5_000_000),
            "item_count": quantity,
            "delivery_fee": rng.uniform(-1_000, 200_000),
            "promo_code": rng.choice((None, "SAVE")),
            "first_add_at": (NOW - timedelta(seconds=rng.uniform(-10, 10_000))).isoformat(),
            "items": (
                [{"product_id": "p1", "quantity": quantity, "unit_price": rng.uniform(1, 3_000_000)}]
                if quantity
                else []
            ),
        })
        state.counters = {
            name: rng.randint(-50, 200) for name in COUNTER_DEFAULTS
        }
        shown_count = rng.randint(0, 25)
        state.interventions = {
            "shown": [
                {"intervention_id": f"I-{rng.randint(1, 20)}"}
                for _ in range(shown_count)
            ],
            "dismissal_count": rng.randint(-5, 30),
            "click_count": rng.randint(-5, 30),
            "last_shown_at": (NOW - timedelta(seconds=rng.uniform(-10, 10_000))).isoformat(),
        }
        history = UserHistory(
            as_of=NOW,
            lifetime_orders=rng.randint(-10, 20_000),
            prior_abandonment_rate=rng.uniform(-2, 3),
            avg_order_value=rng.uniform(-10_000, 2_000_000),
            discount_usage_rate=rng.uniform(-2, 3),
            days_since_last_purchase=rng.uniform(-100, 800),
            avg_session_to_purchase_s=rng.uniform(-100, 200_000),
            return_rate=rng.uniform(-1, 2),
            products={"p1": product},
        )

        started = perf_counter()
        features = compute_features(state, history)
        timings_ms.append((perf_counter() - started) * 1_000)

        assert tuple(features) == FEATURE_NAMES
        for spec in FEATURE_SCHEMA_V1:
            assert spec.minimum <= features[spec.name] <= spec.maximum

    p95_ms = sorted(timings_ms)[949]
    assert p95_ms < 20, f"feature computation p95 was {p95_ms:.3f} ms"
