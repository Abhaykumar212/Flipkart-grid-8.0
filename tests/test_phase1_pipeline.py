import warnings

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from backend.main import SessionFeatures, _load_artifacts, _risk_tier, predict_abandonment
from ml.feature_engineering import ALL_FEATURE_NAMES, RAW_FEATURE_NAMES, engineer_features
from ml.generate_dataset import (
    BAYES_PROBABILITY_NAME,
    FEATURE_NAMES,
    TARGET_NAME,
    generate_dataset,
)


def _sample_session(**overrides):
    """A mid-risk session; individual tests override the fields they care about."""
    base = {
        "seconds_spent_in_cart": 240.0,
        "times_returned_to_product_page": 3,
        "product_reviews_read": 2,
        "seconds_idle_before_checkout": 60.0,
        "delivery_pincode_checks": 1,
        "saved_items_in_wishlist": 2,
        "cart_value_vs_typical_order": 1.4,
        "delivery_fee_percent_of_cart": 4.0,
        "price_dropped_since_first_view": 0,
        "discount_seeking_tendency": 0.5,
        "failed_coupon_attempts": 1,
        "estimated_delivery_days": 4,
        "payment_method_on_file": 0,
        "checkout_steps_completed": 1,
        "payment_attempts_failed": 0,
        "is_guest_checkout": 1,
        "past_abandonment_rate": 0.5,
        "past_order_return_rate": 0.1,
        "lifetime_orders_placed": 4,
        "days_since_last_purchase": 60.0,
        "is_mobile_session": 1,
        "is_late_night_session": 0,
    }
    base.update(overrides)
    return SessionFeatures(**base)


@pytest.fixture(scope="module")
def dataset():
    return generate_dataset(row_count=20_000, seed=7)


@pytest.fixture(scope="module")
def _loaded_artifacts():
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _load_artifacts()
    except Exception as error:
        pytest.skip(str(error))


def test_exact_schema_and_ranges(dataset):
    assert list(dataset.columns) == [*FEATURE_NAMES, TARGET_NAME, BAYES_PROBABILITY_NAME]
    assert len(dataset) == 20_000
    assert len(FEATURE_NAMES) == 22

    bounds = {
        "seconds_spent_in_cart": (10, 900),
        "times_returned_to_product_page": (0, 10),
        "product_reviews_read": (0, 8),
        "seconds_idle_before_checkout": (0, 300),
        "delivery_pincode_checks": (0, 5),
        "cart_value_vs_typical_order": (0.1, 6.0),
        "delivery_fee_percent_of_cart": (0, 25),
        "estimated_delivery_days": (1, 10),
        "checkout_steps_completed": (0, 3),
        "payment_attempts_failed": (0, 5),
        "past_order_return_rate": (0, 0.5),
        "days_since_last_purchase": (0, 400),
    }
    for column, (low, high) in bounds.items():
        assert dataset[column].between(low, high).all(), f"{column} outside [{low}, {high}]"


def test_binary_features_are_binary(dataset):
    for column in (
        "price_dropped_since_first_view",
        "payment_method_on_file",
        "is_guest_checkout",
        "is_mobile_session",
        "is_late_night_session",
        TARGET_NAME,
    ):
        assert set(dataset[column].unique()) <= {0, 1}, column


def test_documented_abandonment_drivers_move_in_expected_direction(dataset):
    """Each assertion maps to a published cart-abandonment driver."""
    overall = dataset[TARGET_NAME].mean()

    def rate(mask):
        return dataset[mask][TARGET_NAME].mean()

    assert rate(dataset["delivery_fee_percent_of_cart"] > 8) > overall + 0.08
    assert rate(dataset["cart_value_vs_typical_order"] > 2.0) > overall + 0.08
    assert rate(dataset["payment_attempts_failed"] > 0) > overall + 0.07
    assert rate(dataset["is_guest_checkout"] == 1) > overall + 0.04
    assert rate(dataset["estimated_delivery_days"] > 5) > overall + 0.03
    assert rate(dataset["checkout_steps_completed"] == 3) < overall - 0.10
    assert rate(dataset["payment_method_on_file"] == 1) < overall - 0.07


def test_bayes_column_is_a_valid_probability_and_beats_chance(dataset):
    bayes = dataset[BAYES_PROBABILITY_NAME]
    assert bayes.between(0.0, 1.0).all()
    auc = roc_auc_score(dataset[TARGET_NAME], bayes)
    assert 0.70 < auc < 0.95


def test_feature_output_shape_and_order():
    frame = generate_dataset(row_count=200, seed=3)
    engineered = engineer_features(frame[RAW_FEATURE_NAMES])
    assert list(engineered.columns) == ALL_FEATURE_NAMES
    assert len(engineered) == 200


def test_no_target_or_oracle_can_leak_through():
    frame = generate_dataset(row_count=100, seed=4)
    engineered = engineer_features(frame)
    assert TARGET_NAME not in engineered.columns
    assert BAYES_PROBABILITY_NAME not in engineered.columns


def test_engineered_features_are_finite():
    frame = generate_dataset(row_count=2_000, seed=5)
    engineered = engineer_features(frame[RAW_FEATURE_NAMES])
    assert np.isfinite(engineered.to_numpy()).all()


def test_response_contains_probability_confidence_and_all_shap_impacts(_loaded_artifacts):
    response = predict_abandonment(_sample_session())

    assert response.status == "success"
    assert 0 <= response.abandonment_probability <= 1
    assert response.confidence_score == pytest.approx(
        abs(response.abandonment_probability - 0.5) * 2,
        abs=1e-5,
    )
    assert set(response.feature_impacts) == set(ALL_FEATURE_NAMES)
    assert len(response.top_contributing_features) <= 3
    assert all(item.shap_value > 0 for item in response.top_contributing_features)
    assert response.risk_tier in {"low", "medium", "high"}


def test_checkout_progress_reduces_predicted_risk(_loaded_artifacts):
    early = predict_abandonment(_sample_session(checkout_steps_completed=0))
    late = predict_abandonment(_sample_session(checkout_steps_completed=3))
    assert late.abandonment_probability < early.abandonment_probability


def test_payment_failures_increase_predicted_risk(_loaded_artifacts):
    clean = predict_abandonment(_sample_session(payment_attempts_failed=0))
    failing = predict_abandonment(_sample_session(payment_attempts_failed=3))
    assert failing.abandonment_probability > clean.abandonment_probability


def test_saved_card_reduces_predicted_risk(_loaded_artifacts):
    guest = predict_abandonment(_sample_session(payment_method_on_file=0))
    saved = predict_abandonment(_sample_session(payment_method_on_file=1))
    assert saved.abandonment_probability < guest.abandonment_probability


@pytest.mark.parametrize(
    ("probability", "expected"),
    ((0.95, "high"), (0.70, "medium"), (0.10, "low")),
)
def test_risk_tier_matches_documented_thresholds(probability, expected):
    assert _risk_tier(probability) == expected
