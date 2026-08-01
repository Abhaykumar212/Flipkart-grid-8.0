"""Generate a synthetic cart-abandonment training dataset.

Design principles
-----------------
1. **Every feature is one a real Flipkart session can actually observe.** Nothing
   here requires data a production tracker could not collect in real time.

2. **Effect directions and relative magnitudes follow published cart-abandonment
   research** (Baymard Institute's recurring checkout-abandonment survey), not
   whatever maximises model score. The headline documented reasons shoppers give
   for abandoning are: extra costs too high (~48%), forced account creation
   (~26%), didn't trust the site with card details (~25%), delivery too slow
   (~23%), and checkout too long/complex (~18%). Each of those has a
   corresponding observable feature below.

3. **Latent shopper traits drive several observables at once**, so features are
   realistically correlated rather than independent — a purely independent
   feature matrix would make the learning problem artificially easy.

4. **Irreducible noise is retained.** Human purchase decisions are not a
   deterministic function of telemetry. The noise term is what keeps this at a
   realistic difficulty; see `true_probability` below.

`bayes_optimal_probability` column
----------------------------------
The generator also emits the **Bayes-optimal probability**: P(abandon | observable
features), obtained by integrating the decision noise out of the signal via
Gauss-Hermite quadrature.

This is deliberately NOT `sigmoid(signal_including_realised_noise)`. That
quantity would peek at the unobservable noise draw and therefore describe an
oracle no model could ever match — using it as a "ceiling" would understate how
good our model actually is. Marginalising the noise gives the genuine upper
bound for any model restricted to the observable feature set.

The column is NEVER used as a model feature — `train_model.py` drops it
explicitly and asserts it is absent from the training matrix. It exists so we
can report the model's distance from the theoretical maximum, which is far more
informative than a raw AUC in isolation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROW_COUNT = 200_000
RANDOM_SEED = 42
TARGET_ABANDONMENT_RATE = 0.68  # Industry-reported average sits near 70%.
DATA_PATH = Path(__file__).resolve().parent / "data" / "cart_abandonment_dataset.csv"

# Irreducible noise in the decision process. Kept deliberately non-trivial:
# a real shopper's final click depends on context no tracker can see (a phone
# call, a partner's opinion, payday timing).
DECISION_NOISE_SIGMA = 0.55

FEATURE_NAMES = [
    # --- A. Cart engagement: how invested is this shopper in this cart? ---
    "seconds_spent_in_cart",
    "times_returned_to_product_page",
    "product_reviews_read",
    "seconds_idle_before_checkout",
    "delivery_pincode_checks",
    "saved_items_in_wishlist",
    # --- B. Cost friction: the #1 documented abandonment driver ---
    "cart_value_vs_typical_order",
    "delivery_fee_percent_of_cart",
    "price_dropped_since_first_view",
    "discount_seeking_tendency",
    "failed_coupon_attempts",
    # --- C. Delivery friction ---
    "estimated_delivery_days",
    # --- D. Checkout & trust friction ---
    "payment_method_on_file",
    "checkout_steps_completed",
    "payment_attempts_failed",
    "is_guest_checkout",
    # --- E. Customer history (RFM-style) ---
    "past_abandonment_rate",
    "past_order_return_rate",
    "lifetime_orders_placed",
    "days_since_last_purchase",
    # --- F. Session context ---
    "is_mobile_session",
    "is_late_night_session",
]

TARGET_NAME = "is_abandoned"
BAYES_PROBABILITY_NAME = "bayes_optimal_probability"


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30.0, 30.0)))


def _marginalise_noise(
    deterministic_signal: np.ndarray,
    intercept: float,
    sigma: float,
    quadrature_points: int = 81,
) -> np.ndarray:
    """P(abandon | observable features), integrating out the decision noise.

    The label is drawn as Bernoulli(sigmoid(det + intercept + eps)) with
    eps ~ N(0, sigma). A model that sees only the observable features cannot
    know `eps`, so the best it can do is the expectation over it. Computed with
    Gauss-Hermite quadrature, which is exact for this smooth 1-D integral.
    """
    nodes, weights = np.polynomial.hermite_e.hermegauss(quadrature_points)
    z = deterministic_signal[:, None] + intercept + sigma * nodes[None, :]
    return (_sigmoid(z) * weights[None, :]).sum(axis=1) / np.sqrt(2.0 * np.pi)


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

    # ------------------------------------------------------------------
    # Latent shopper traits. Not observable, but they induce the realistic
    # correlations between the observable features below.
    # ------------------------------------------------------------------
    deliberation = rng.beta(2.0, 2.4, row_count)          # research-heavy vs impulsive
    price_pressure = rng.beta(2.1, 2.0, row_count)        # budget sensitivity
    delivery_sensitivity = rng.beta(1.8, 2.8, row_count)  # cares about speed
    checkout_readiness = rng.beta(2.5, 1.9, row_count)    # account set up, ready to pay
    loyalty = rng.beta(1.7, 2.6, row_count)               # tenure with the platform

    # ------------------------------------------------------------------
    # F. Session context
    # Mobile sessions convert materially worse than desktop across the
    # industry — smaller screens, more interruption, fiddlier payment entry.
    # ------------------------------------------------------------------
    is_mobile_session = rng.binomial(1, 0.62, row_count).astype(int)
    # Late-night browsing skews toward low-intent "window shopping".
    is_late_night_session = rng.binomial(
        1, np.clip(0.13 + 0.10 * deliberation, 0.0, 0.5)
    ).astype(int)

    # ------------------------------------------------------------------
    # A. Cart engagement
    # ------------------------------------------------------------------
    times_returned_to_product_page = np.clip(
        rng.poisson(0.45 + 4.1 * deliberation + 1.0 * price_pressure), 0, 10
    ).astype(int)
    product_reviews_read = rng.binomial(
        8, np.clip(0.04 + 0.58 * deliberation, 0.0, 0.88)
    ).astype(int)
    seconds_spent_in_cart = np.clip(
        rng.gamma(1.8 + 2.0 * deliberation, 76.0, row_count)
        + 26.0 * times_returned_to_product_page,
        10.0,
        900.0,
    ).round(2)
    seconds_idle_before_checkout = np.clip(
        300.0 * rng.beta(1.0 + 2.5 * deliberation, 3.8 + checkout_readiness),
        0.0,
        300.0,
    ).round(2)
    saved_items_in_wishlist = np.clip(
        rng.poisson(0.35 + 2.1 * deliberation), 0, 20
    ).astype(int)

    # ------------------------------------------------------------------
    # C. Delivery friction
    # ------------------------------------------------------------------
    estimated_delivery_days = rng.choice(
        np.arange(1, 11),
        row_count,
        p=[0.07, 0.13, 0.17, 0.17, 0.15, 0.11, 0.08, 0.06, 0.04, 0.02],
    ).astype(int)
    # Shoppers re-check the pincode when they are worried about the date.
    delivery_pincode_checks = rng.binomial(
        5,
        np.clip(
            0.03
            + 0.32 * delivery_sensitivity
            + 0.035 * np.maximum(estimated_delivery_days - 3, 0),
            0.0,
            0.92,
        ),
    ).astype(int)

    # ------------------------------------------------------------------
    # B. Cost friction
    # ------------------------------------------------------------------
    cart_value_vs_typical_order = np.clip(
        rng.lognormal(
            mean=np.log(0.82 + 0.85 * price_pressure), sigma=0.42, size=row_count
        ),
        0.1,
        6.0,
    ).round(4)
    charges_delivery_fee = rng.random(row_count) < (
        0.38 + 0.18 * (cart_value_vs_typical_order < 0.8)
    )
    delivery_fee_percent_of_cart = np.where(
        charges_delivery_fee,
        15.0 * rng.beta(1.35 + 1.8 * price_pressure, 2.4, row_count),
        0.0,
    )
    delivery_fee_percent_of_cart = np.clip(
        delivery_fee_percent_of_cart, 0.0, 25.0
    ).round(4)

    discount_seeking_tendency = np.clip(
        0.62 * price_pressure + 0.38 * rng.beta(1.7, 2.1, row_count), 0.0, 1.0
    ).round(4)
    price_dropped_since_first_view = rng.binomial(
        1, np.clip(0.18 + 0.22 * discount_seeking_tendency, 0.0, 0.65)
    ).astype(int)
    # Coupon hunters try codes; failures are a documented abandonment trigger.
    failed_coupon_attempts = np.clip(
        rng.poisson(0.15 + 1.9 * discount_seeking_tendency), 0, 6
    ).astype(int)

    # ------------------------------------------------------------------
    # E. Customer history
    # ------------------------------------------------------------------
    past_abandonment_rate = np.clip(
        rng.beta(2.0 + 1.6 * deliberation, 2.4 + checkout_readiness, row_count), 0.0, 1.0
    ).round(4)
    past_order_return_rate = np.clip(
        0.5 * rng.beta(1.25 + deliberation, 5.0, row_count), 0.0, 0.5
    ).round(4)
    lifetime_orders_placed = np.clip(
        rng.poisson(0.6 + 22.0 * loyalty), 0, 120
    ).astype(int)
    # Loyal, recently-active customers come back sooner.
    days_since_last_purchase = np.clip(
        rng.gamma(1.6, 30.0 * (1.25 - loyalty), row_count), 0.0, 400.0
    ).round(1)

    # ------------------------------------------------------------------
    # D. Checkout & trust friction
    # ------------------------------------------------------------------
    payment_method_on_file = rng.binomial(
        1,
        np.clip(
            0.16
            + 0.50 * checkout_readiness
            + 0.22 * loyalty
            - 0.18 * past_abandonment_rate,
            0.03,
            0.94,
        ),
    ).astype(int)
    # Guest checkout correlates with low tenure — forced account creation is a
    # top-3 documented abandonment reason.
    is_guest_checkout = rng.binomial(
        1, np.clip(0.55 - 0.42 * loyalty - 0.12 * checkout_readiness, 0.02, 0.9)
    ).astype(int)
    # How far into the 3-step checkout funnel the shopper actually got.
    checkout_steps_completed = np.clip(
        rng.binomial(3, np.clip(0.28 + 0.55 * checkout_readiness, 0.05, 0.95)), 0, 3
    ).astype(int)
    # Payment failures are a hard blocker, and more common without a saved card.
    payment_attempts_failed = np.clip(
        rng.poisson(
            np.where(payment_method_on_file == 1, 0.06, 0.42)
            * (1.0 + 0.8 * (checkout_steps_completed >= 2))
        ),
        0,
        5,
    ).astype(int)

    # ------------------------------------------------------------------
    # Interaction hypotheses. These are DOMAIN CLAIMS about how frictions
    # compound — deliberately expressed as smooth products of normalised
    # quantities rather than hard thresholds, so the model has to learn the
    # shape rather than being handed a matching indicator column.
    # ------------------------------------------------------------------
    cost_shock = (
        np.clip(cart_value_vs_typical_order / 2.0, 0.0, 1.5)
        * np.clip(delivery_fee_percent_of_cart / 10.0, 0.0, 1.5)
    )
    research_spiral = (
        np.clip(times_returned_to_product_page / 5.0, 0.0, 1.5)
        * np.clip(product_reviews_read / 4.0, 0.0, 1.5)
    )
    # Expensive cart on a phone: small screen + fiddly payment entry.
    mobile_high_value = is_mobile_session * np.clip(
        cart_value_vs_typical_order / 2.0, 0.0, 1.5
    )
    # Trust barrier: spending a lot without an account.
    guest_high_value = is_guest_checkout * np.clip(
        cart_value_vs_typical_order / 2.0, 0.0, 1.5
    )
    # Lapsed customer re-engaging with a big basket is a fragile conversion.
    lapsed_big_basket = np.clip(days_since_last_purchase / 180.0, 0.0, 1.5) * np.clip(
        cart_value_vs_typical_order / 2.0, 0.0, 1.5
    )

    # ------------------------------------------------------------------
    # Decision signal (log-odds of abandonment).
    # Sign and rough magnitude of every term is justified in FEATURE_RATIONALE.
    # ------------------------------------------------------------------
    deterministic_signal = (
        # A. Engagement — deliberation mildly raises abandonment; commitment lowers it.
        0.0013 * (seconds_spent_in_cart - 200.0)
        + 0.09 * times_returned_to_product_page
        + 0.07 * product_reviews_read
        + 0.0022 * seconds_idle_before_checkout
        + 0.07 * delivery_pincode_checks
        - 0.030 * saved_items_in_wishlist
        # B. Cost friction — the dominant documented driver.
        + 0.42 * (cart_value_vs_typical_order - 1.0)
        + 0.075 * delivery_fee_percent_of_cart
        - 0.40 * price_dropped_since_first_view
        + 0.34 * (discount_seeking_tendency - 0.5)
        + 0.26 * failed_coupon_attempts
        # C. Delivery friction.
        + 0.11 * (estimated_delivery_days - 4)
        # D. Checkout & trust friction — strongest single lever.
        - 0.62 * payment_method_on_file
        - 0.78 * checkout_steps_completed
        + 0.71 * payment_attempts_failed
        + 0.45 * is_guest_checkout
        # E. Customer history.
        + 0.95 * (past_abandonment_rate - 0.5)
        + 0.85 * past_order_return_rate
        - 0.016 * lifetime_orders_placed
        + 0.0022 * days_since_last_purchase
        # F. Session context.
        + 0.28 * is_mobile_session
        + 0.33 * is_late_night_session
        # Compounding friction hypotheses.
        + 0.85 * cost_shock
        + 0.70 * research_spiral
        + 0.40 * mobile_high_value
        + 0.46 * guest_high_value
        + 0.38 * lapsed_big_basket
    )

    # Irreducible: the part of a human decision telemetry cannot see.
    decision_noise = rng.normal(0.0, DECISION_NOISE_SIGMA, row_count)

    intercept = _calibrate_intercept(
        deterministic_signal + decision_noise, TARGET_ABANDONMENT_RATE
    )
    # Labels are drawn using the realised noise draw...
    is_abandoned = rng.binomial(
        1, _sigmoid(deterministic_signal + decision_noise + intercept)
    ).astype(int)
    # ...but the reported ceiling marginalises it out, because no model that
    # sees only the observable features can ever recover that draw.
    bayes_optimal_probability = _marginalise_noise(
        deterministic_signal, intercept, DECISION_NOISE_SIGMA
    )

    dataset = pd.DataFrame(
        {
            "seconds_spent_in_cart": seconds_spent_in_cart,
            "times_returned_to_product_page": times_returned_to_product_page,
            "product_reviews_read": product_reviews_read,
            "seconds_idle_before_checkout": seconds_idle_before_checkout,
            "delivery_pincode_checks": delivery_pincode_checks,
            "saved_items_in_wishlist": saved_items_in_wishlist,
            "cart_value_vs_typical_order": cart_value_vs_typical_order,
            "delivery_fee_percent_of_cart": delivery_fee_percent_of_cart,
            "price_dropped_since_first_view": price_dropped_since_first_view,
            "discount_seeking_tendency": discount_seeking_tendency,
            "failed_coupon_attempts": failed_coupon_attempts,
            "estimated_delivery_days": estimated_delivery_days,
            "payment_method_on_file": payment_method_on_file,
            "checkout_steps_completed": checkout_steps_completed,
            "payment_attempts_failed": payment_attempts_failed,
            "is_guest_checkout": is_guest_checkout,
            "past_abandonment_rate": past_abandonment_rate,
            "past_order_return_rate": past_order_return_rate,
            "lifetime_orders_placed": lifetime_orders_placed,
            "days_since_last_purchase": days_since_last_purchase,
            "is_mobile_session": is_mobile_session,
            "is_late_night_session": is_late_night_session,
            TARGET_NAME: is_abandoned,
            BAYES_PROBABILITY_NAME: bayes_optimal_probability.round(6),
        },
        columns=[*FEATURE_NAMES, TARGET_NAME, BAYES_PROBABILITY_NAME],
    )
    return dataset


# Presentation aid: the one-line "why is this feature here?" answer for each
# feature, so the rationale lives next to the code that produces it.
FEATURE_RATIONALE: dict[str, str] = {
    "seconds_spent_in_cart": "Dwell time in cart. Long dwell without checkout indicates deliberation rather than intent.",
    "times_returned_to_product_page": "Cart-to-PDP bouncing. Re-opening the product signals unresolved doubt about the item.",
    "product_reviews_read": "Depth of review research. Heavy review reading late in the funnel correlates with uncertainty.",
    "seconds_idle_before_checkout": "Inactivity immediately before checkout — the classic hesitation window.",
    "delivery_pincode_checks": "Repeated pincode checks reveal anxiety about whether delivery works for them.",
    "saved_items_in_wishlist": "Wishlist size proxies platform engagement; engaged shoppers abandon less.",
    "cart_value_vs_typical_order": "Basket size relative to this shopper's own average order — captures sticker shock personally, not absolutely.",
    "delivery_fee_percent_of_cart": "Shipping cost as share of basket. 'Extra costs too high' is the single most cited abandonment reason (~48%).",
    "price_dropped_since_first_view": "A recent price drop creates urgency and reduces abandonment.",
    "discount_seeking_tendency": "Coupon-hunting profile. Deal-driven shoppers abandon more when no deal materialises.",
    "failed_coupon_attempts": "Failed promo-code entries. 'Couldn't find a working coupon' is a documented trigger.",
    "estimated_delivery_days": "Promised delivery speed. 'Delivery too slow' is cited by roughly a quarter of abandoners.",
    "payment_method_on_file": "A saved card removes the highest-friction checkout step and is a strong conversion signal.",
    "checkout_steps_completed": "How deep into the 3-step funnel the shopper reached — the best available proxy for commitment.",
    "payment_attempts_failed": "Declined or errored payments. A hard blocker, not a preference — highly actionable for Phase 2.",
    "is_guest_checkout": "Checking out without an account. Forced/absent account flows are a top-3 cited reason (~26%).",
    "past_abandonment_rate": "This shopper's own historical abandonment behaviour — the strongest available prior.",
    "past_order_return_rate": "High return rates indicate prior dissatisfaction and lower purchase conviction.",
    "lifetime_orders_placed": "Purchase frequency (the F in RFM). Loyal buyers convert more reliably.",
    "days_since_last_purchase": "Recency (the R in RFM). Lapsed shoppers are materially less likely to complete.",
    "is_mobile_session": "Mobile sessions convert worse than desktop across the industry — smaller screens, more interruption.",
    "is_late_night_session": "Late-night sessions skew toward low-intent browsing rather than buying.",
}


def _print_quality_report(dataset: pd.DataFrame) -> None:
    target = dataset[TARGET_NAME]
    overall = float(target.mean())

    print(f"Rows: {len(dataset):,}")
    print(f"Features: {len(FEATURE_NAMES)}")
    print(f"Overall abandonment rate: {overall:.2%}\n")

    print("Abandonment rate by documented driver:")
    segments = {
        "Delivery fee > 8% of cart": dataset["delivery_fee_percent_of_cart"] > 8,
        "Cart > 2x typical order": dataset["cart_value_vs_typical_order"] > 2.0,
        "Any failed payment attempt": dataset["payment_attempts_failed"] > 0,
        "Reached final checkout step": dataset["checkout_steps_completed"] == 3,
        "Guest checkout": dataset["is_guest_checkout"] == 1,
        "Saved payment method": dataset["payment_method_on_file"] == 1,
        "Delivery > 5 days": dataset["estimated_delivery_days"] > 5,
        "Failed coupon attempts": dataset["failed_coupon_attempts"] > 0,
        "Mobile session": dataset["is_mobile_session"] == 1,
        "Lapsed > 180 days": dataset["days_since_last_purchase"] > 180,
    }
    for label, mask in segments.items():
        rate = float(target[mask].mean())
        share = float(mask.mean())
        delta = rate - overall
        print(f"  {label:<32} {rate:6.2%}  ({delta:+.2%} vs base, {share:.1%} of rows)")


if __name__ == "__main__":
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame = generate_dataset()
    frame.to_csv(DATA_PATH, index=False)
    print(f"Saved dataset to {DATA_PATH}\n")
    _print_quality_report(frame)
