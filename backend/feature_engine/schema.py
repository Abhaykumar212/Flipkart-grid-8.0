from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from math import isfinite
from pathlib import Path
from typing import Literal, Mapping


FEATURE_SCHEMA_VERSION = "fs-v1"


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    """One ordered entry in the serving/training feature contract."""

    name: str
    dtype: Literal["int", "float"]
    minimum: float
    maximum: float
    default: float

    def to_dict(self) -> dict[str, str | float]:
        data = asdict(self)
        data["type"] = data.pop("dtype")
        return data


@dataclass(frozen=True, slots=True)
class ProductFacts:
    """Stable catalogue facts needed by the feature engine."""

    product_id: str
    category: str
    mrp: float
    selling_price: float
    rating: float
    rating_count: int
    in_stock: bool
    quantity_left: int
    estimated_delivery_days: int
    emi_eligible: bool
    price_history: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class UserHistory:
    """Historical and catalogue context supplied to ``compute_features``.

    Defaults are the explicit cold-start priors in IMPLEMENTATION_PLAN.md §9.2.
    Keeping the observation time here makes simulation, tests, and serving use
    the exact same two-argument feature function.
    """

    as_of: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lifetime_orders: int = 0
    prior_abandonment_rate: float = 0.5
    avg_order_value: float = 15_000.0
    discount_usage_rate: float = 0.3
    category_order_counts: Mapping[str, int] = field(default_factory=dict)
    days_since_last_purchase: float = 365.0
    avg_session_to_purchase_s: float = 900.0
    return_rate: float = 0.08
    affinity_informational: float = 0.5
    affinity_incentive: float = 0.5
    payment_method_on_file: bool = False
    products: Mapping[str, ProductFacts] = field(default_factory=dict)


def _spec(
    name: str,
    dtype: Literal["int", "float"],
    minimum: float,
    maximum: float,
    default: float = 0.0,
) -> FeatureSpec:
    return FeatureSpec(name, dtype, minimum, maximum, default)


# §9.2, in the frozen serving order. Bounds not explicitly narrow in the plan
# use generous finite operational caps so malformed inputs can never produce
# infinities while real catalogue values remain untouched.
FEATURE_SCHEMA_V1: tuple[FeatureSpec, ...] = (
    # Group 1 — user history (11)
    _spec("u_lifetime_orders", "int", 0, 10_000),
    _spec("u_prior_abandonment_rate", "float", 0, 1, 0.5),
    _spec("u_avg_order_value", "float", 0, 1_000_000, 15_000),
    _spec("u_discount_usage_rate", "float", 0, 1, 0.3),
    _spec("u_category_affinity", "float", 0, 1),
    _spec("u_days_since_last_purchase", "float", 0, 400, 365),
    _spec("u_avg_session_to_purchase_s", "float", 0, 86_400, 900),
    _spec("u_return_rate", "float", 0, 0.5, 0.08),
    _spec("u_is_new_user", "int", 0, 1, 1),
    _spec("u_affinity_informational", "float", 0, 1, 0.5),
    _spec("u_affinity_incentive", "float", 0, 1, 0.5),
    # Group 2 — cart (9)
    _spec("c_value", "float", 0, 2_000_000),
    _spec("c_item_count", "int", 0, 20),
    _spec("c_distinct_categories", "int", 0, 5),
    _spec("c_value_to_aov_ratio", "float", 0, 6),
    _spec("c_discount_pct_available", "float", 0, 100),
    _spec("c_age_seconds", "float", 0, 3_600),
    _spec("c_promo_applied", "int", 0, 1),
    _spec("c_max_price_drop_pct", "float", 0, 50),
    _spec("c_price_increased_since_view", "int", 0, 1),
    # Group 3 — product (5)
    _spec("p_max_item_price", "float", 0, 2_000_000),
    _spec("p_avg_rating", "float", 1, 5, 4),
    _spec("p_min_rating_count", "int", 0, 100_000_000),
    _spec("p_any_low_stock", "int", 0, 1),
    _spec("p_any_out_of_stock", "int", 0, 1),
    # Group 4 — delivery (5)
    _spec("d_max_days", "int", 1, 10, 5),
    _spec("d_min_days", "int", 1, 10, 5),
    _spec("d_fee", "float", 0, 100_000),
    _spec("d_fee_pct_of_cart", "float", 0, 25),
    _spec("d_check_count", "int", 0, 10),
    # Group 5 — payment (5)
    _spec("pay_method_on_file", "int", 0, 1),
    _spec("pay_failure_count", "int", 0, 5),
    _spec("pay_method_change_count", "int", 0, 5),
    _spec("pay_emi_eligible", "int", 0, 1),
    _spec("pay_checkout_max_step", "int", 0, 3),
    # Group 6 — session behavior (18)
    _spec("s_duration_seconds", "float", 0, 3_600),
    _spec("s_product_view_count", "int", 0, 60),
    _spec("s_distinct_products_viewed", "int", 0, 40),
    _spec("s_review_open_count", "int", 0, 20),
    _spec("s_review_dwell_seconds", "float", 0, 900),
    _spec("s_similar_product_view_count", "int", 0, 30),
    _spec("s_comparison_count", "int", 0, 15),
    _spec("s_cart_view_count", "int", 0, 20),
    _spec("s_cart_add_count", "int", 0, 20),
    _spec("s_cart_remove_count", "int", 0, 20),
    _spec("s_cart_product_switch_count", "int", 0, 20),
    _spec("s_search_count", "int", 0, 20),
    _spec("s_price_sort_count", "int", 0, 10),
    _spec("s_coupon_search_count", "int", 0, 10),
    _spec("s_checkout_start_count", "int", 0, 5),
    _spec("s_back_from_checkout_count", "int", 0, 5),
    _spec("s_idle_seconds_current", "float", 0, 900),
    _spec("s_event_velocity_per_min", "float", 0, 60),
    # Group 7 — context (9)
    _spec("x_is_mobile", "int", 0, 1),
    _spec("x_hour_of_day", "int", 0, 23, 12),
    _spec("x_is_late_night", "int", 0, 1),
    _spec("x_is_weekend", "int", 0, 1),
    _spec("x_is_returning_user", "int", 0, 1),
    _spec("x_referral_direct", "int", 0, 1, 1),
    _spec("x_referral_search", "int", 0, 1),
    _spec("x_referral_social", "int", 0, 1),
    _spec("x_referral_email", "int", 0, 1),
    # Group 8 — intervention history (5; deliberately excluded from risk)
    _spec("i_shown_count", "int", 0, 10),
    _spec("i_dismissal_count", "int", 0, 10),
    _spec("i_click_count", "int", 0, 10),
    _spec("i_seconds_since_last", "float", 0, 3_600, 3_600),
    _spec("i_distinct_types_shown", "int", 0, 12),
)

FEATURE_NAMES = tuple(spec.name for spec in FEATURE_SCHEMA_V1)
FEATURE_BY_NAME = {spec.name: spec for spec in FEATURE_SCHEMA_V1}
RISK_MODEL_FEATURES = tuple(name for name in FEATURE_NAMES if not name.startswith("i_"))

assert len(FEATURE_SCHEMA_V1) == 67
assert len(FEATURE_BY_NAME) == 67
assert len(RISK_MODEL_FEATURES) == 62


def clamp_feature(name: str, value: float | int | bool | None) -> float:
    """Convert a computed value to a finite float inside its schema bounds."""

    spec = FEATURE_BY_NAME[name]
    try:
        numeric = float(value) if value is not None else spec.default
    except (TypeError, ValueError):
        numeric = spec.default
    if not isfinite(numeric):
        numeric = spec.default
    numeric = min(spec.maximum, max(spec.minimum, numeric))
    if spec.dtype == "int":
        numeric = float(int(numeric))
    return numeric


def feature_schema_document() -> dict[str, object]:
    """Return the JSON-ready artifact contract used by model loaders."""

    return {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "features": [spec.to_dict() for spec in FEATURE_SCHEMA_V1],
        "risk_model_features": list(RISK_MODEL_FEATURES),
    }


def serialize_feature_schema(*, indent: int | None = 2) -> str:
    return json.dumps(feature_schema_document(), indent=indent, sort_keys=False)


def write_feature_schema(path: str | Path) -> None:
    Path(path).write_text(serialize_feature_schema() + "\n", encoding="utf-8")
