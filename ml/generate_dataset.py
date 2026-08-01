"""Generate a realistic synthetic cart-abandonment training dataset.

The target is sampled from a non-linear probability model with interacting
behavioural, pricing, delivery, historical, and checkout signals. It is not a
deterministic copy of any individual feature or threshold.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROW_COUNT = 200_000
RANDOM_SEED = 42
TARGET_ABANDONMENT_RATE = 0.65
DATA_PATH = Path(__file__).resolve().parent / "data" / "cart_abandonment_dataset.csv"

FEATURE_NAMES = [
    "cart_dwell_time_seconds",
    "cart_pdp_bounce_count",
    "reviews_expanded_count",
    "idle_time_before_checkout",
    "delivery_pincode_checked",
    "cart_value_to_aov_ratio",
    "delivery_fee_percentage",
    "est_delivery_days",
    "has_price_dropped_recently",
    "hist_abandonment_rate",
    "discount_sensitivity_score",
    "past_return_rate",
    "wishlist_item_count",
    "payment_method_saved",
]


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30.0, 30.0)))


def _calibrate_intercept(signal: np.ndarray, target_rate: float) -> float:
    """Find an intercept whose mean probability matches the requested baseline."""
    lower, upper = -12.0, 12.0
    for _ in range(80):
        midpoint = (lower + upper) / 2.0
        if _sigmoid(signal + midpoint).mean() < target_rate:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


def generate_dataset(
    row_count: int = ROW_COUNT,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Latent customer traits produce correlated, non-uniform observable signals.
    deliberation = rng.beta(2.0, 2.4, row_count)
    price_pressure = rng.beta(2.1, 2.0, row_count)
    delivery_sensitivity = rng.beta(1.8, 2.8, row_count)
    checkout_readiness = rng.beta(2.5, 1.9, row_count)

    cart_pdp_bounce_count = np.clip(
        rng.poisson(0.45 + 4.1 * deliberation + 1.0 * price_pressure), 0, 10
    ).astype(int)
    reviews_expanded_count = rng.binomial(
        8, np.clip(0.04 + 0.58 * deliberation, 0.0, 0.88)
    ).astype(int)
    cart_dwell_time_seconds = np.clip(
        rng.gamma(1.8 + 2.0 * deliberation, 76.0, row_count)
        + 26.0 * cart_pdp_bounce_count,
        10.0,
        600.0,
    ).round(2)
    idle_time_before_checkout = np.clip(
        300.0 * rng.beta(1.0 + 2.5 * deliberation, 3.8 + checkout_readiness),
        0.0,
        300.0,
    ).round(2)

    est_delivery_days = rng.choice(
        np.arange(1, 11),
        row_count,
        p=[0.07, 0.13, 0.17, 0.17, 0.15, 0.11, 0.08, 0.06, 0.04, 0.02],
    ).astype(int)
    delivery_pincode_checked = rng.binomial(
        5,
        np.clip(
            0.03
            + 0.32 * delivery_sensitivity
            + 0.035 * np.maximum(est_delivery_days - 3, 0),
            0.0,
            0.92,
        ),
    ).astype(int)

    cart_value_to_aov_ratio = np.clip(
        rng.lognormal(
            mean=np.log(0.82 + 0.85 * price_pressure),
            sigma=0.42,
            size=row_count,
        ),
        0.2,
        4.0,
    ).round(4)
    paid_delivery = rng.random(row_count) < (
        0.38 + 0.18 * (cart_value_to_aov_ratio < 0.8)
    )
    delivery_fee_percentage = np.where(
        paid_delivery,
        15.0
        * rng.beta(
            1.35 + 1.8 * price_pressure,
            2.4,
            row_count,
        ),
        0.0,
    )
    delivery_fee_percentage = np.clip(delivery_fee_percentage, 0.0, 15.0).round(4)

    hist_abandonment_rate = np.clip(
        rng.beta(2.0 + 1.6 * deliberation, 2.4 + checkout_readiness, row_count),
        0.0,
        1.0,
    ).round(4)
    discount_sensitivity_score = np.clip(
        0.62 * price_pressure + 0.38 * rng.beta(1.7, 2.1, row_count),
        0.0,
        1.0,
    ).round(4)
    past_return_rate = np.clip(
        0.5 * rng.beta(1.25 + deliberation, 5.0, row_count), 0.0, 0.5
    ).round(4)
    wishlist_item_count = np.clip(
        rng.poisson(0.35 + 2.1 * deliberation), 0, 5
    ).astype(int)
    has_price_dropped_recently = rng.binomial(
        1, np.clip(0.18 + 0.22 * discount_sensitivity_score, 0.0, 0.65)
    ).astype(int)
    payment_method_saved = rng.binomial(
        1,
        np.clip(
            0.20
            + 0.54 * checkout_readiness
            - 0.20 * hist_abandonment_rate
            - 0.18 * past_return_rate,
            0.04,
            0.92,
        ),
    ).astype(int)

    price_shock = (
        (cart_value_to_aov_ratio > 1.8) & (delivery_fee_percentage > 5.0)
    ).astype(float)
    quality_uncertainty = (
        (cart_pdp_bounce_count > 3) & (reviews_expanded_count > 2)
    ).astype(float)
    long_delivery = (est_delivery_days > 5).astype(float)
    saved_payment_low_value = (
        (payment_method_saved == 1) & (cart_value_to_aov_ratio < 1.0)
    ).astype(float)

    # Substantial irreducible noise keeps classes overlapping and prevents an
    # unrealistically perfect benchmark while preserving required correlations.
    signal = (
        0.0017 * (cart_dwell_time_seconds - 180.0)
        + 0.10 * cart_pdp_bounce_count
        + 0.08 * reviews_expanded_count
        + 0.0025 * idle_time_before_checkout
        + 0.08 * delivery_pincode_checked
        + 0.48 * (cart_value_to_aov_ratio - 1.0)
        + 0.045 * delivery_fee_percentage
        + 0.09 * (est_delivery_days - 4)
        - 0.42 * has_price_dropped_recently
        + 0.90 * (hist_abandonment_rate - 0.5)
        + 0.38 * (discount_sensitivity_score - 0.5)
        + 0.90 * past_return_rate
        - 0.055 * wishlist_item_count
        - 0.48 * payment_method_saved
        + 1.50 * price_shock
        + 1.45 * quality_uncertainty
        + 0.72 * long_delivery
        - 1.20 * saved_payment_low_value
        + rng.normal(0.0, 0.62, row_count)
    )
    intercept = _calibrate_intercept(signal, TARGET_ABANDONMENT_RATE)
    abandonment_probability = _sigmoid(signal + intercept)
    is_abandoned = rng.binomial(1, abandonment_probability).astype(int)

    dataset = pd.DataFrame(
        {
            "cart_dwell_time_seconds": cart_dwell_time_seconds,
            "cart_pdp_bounce_count": cart_pdp_bounce_count,
            "reviews_expanded_count": reviews_expanded_count,
            "idle_time_before_checkout": idle_time_before_checkout,
            "delivery_pincode_checked": delivery_pincode_checked,
            "cart_value_to_aov_ratio": cart_value_to_aov_ratio,
            "delivery_fee_percentage": delivery_fee_percentage,
            "est_delivery_days": est_delivery_days,
            "has_price_dropped_recently": has_price_dropped_recently,
            "hist_abandonment_rate": hist_abandonment_rate,
            "discount_sensitivity_score": discount_sensitivity_score,
            "past_return_rate": past_return_rate,
            "wishlist_item_count": wishlist_item_count,
            "payment_method_saved": payment_method_saved,
            "is_abandoned": is_abandoned,
        },
        columns=[*FEATURE_NAMES, "is_abandoned"],
    )
    return dataset


def _print_quality_report(dataset: pd.DataFrame) -> None:
    target = dataset["is_abandoned"]
    overall = float(target.mean())
    price_shock = (
        (dataset["cart_value_to_aov_ratio"] > 1.8)
        & (dataset["delivery_fee_percentage"] > 5.0)
    )
    quality_uncertainty = (
        (dataset["cart_pdp_bounce_count"] > 3)
        & (dataset["reviews_expanded_count"] > 2)
    )
    long_delivery = dataset["est_delivery_days"] > 5
    saved_low = (
        (dataset["payment_method_saved"] == 1)
        & (dataset["cart_value_to_aov_ratio"] < 1.0)
    )

    print(f"Rows: {len(dataset):,}")
    print(f"Overall abandonment rate: {overall:.2%}")
    print(f"Price-shock abandonment rate: {target[price_shock].mean():.2%}")
    print(f"Quality-uncertainty abandonment rate: {target[quality_uncertainty].mean():.2%}")
    print(f"Long-delivery abandonment rate: {target[long_delivery].mean():.2%}")
    print(f"Saved-payment + low-value abandonment rate: {target[saved_low].mean():.2%}")


if __name__ == "__main__":
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame = generate_dataset()
    frame.to_csv(DATA_PATH, index=False)
    print(f"Saved dataset to {DATA_PATH}")
    _print_quality_report(frame)
