import unittest

from backend.main import SessionFeatures, _load_artifacts, predict_abandonment
from ml.feature_engineering import ALL_FEATURE_NAMES, RAW_FEATURE_NAMES, engineer_features
from ml.generate_dataset import (
    BAYES_PROBABILITY_NAME,
    FEATURE_NAMES,
    TARGET_NAME,
    generate_dataset,
)


def _sample_session(**overrides):
    """A mid-risk session; individual tests override the fields they care about."""
    base = dict(
        seconds_spent_in_cart=240.0,
        times_returned_to_product_page=3,
        product_reviews_read=2,
        seconds_idle_before_checkout=60.0,
        delivery_pincode_checks=1,
        saved_items_in_wishlist=2,
        cart_value_vs_typical_order=1.4,
        delivery_fee_percent_of_cart=4.0,
        price_dropped_since_first_view=0,
        discount_seeking_tendency=0.5,
        failed_coupon_attempts=1,
        estimated_delivery_days=4,
        payment_method_on_file=0,
        checkout_steps_completed=1,
        payment_attempts_failed=0,
        is_guest_checkout=1,
        past_abandonment_rate=0.5,
        past_order_return_rate=0.1,
        lifetime_orders_placed=4,
        days_since_last_purchase=60.0,
        is_mobile_session=1,
        is_late_night_session=0,
    )
    base.update(overrides)
    return SessionFeatures(**base)


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = generate_dataset(row_count=20_000, seed=7)

    def test_exact_schema_and_ranges(self):
        self.assertEqual(
            list(self.dataset.columns),
            [*FEATURE_NAMES, TARGET_NAME, BAYES_PROBABILITY_NAME],
        )
        self.assertEqual(len(self.dataset), 20_000)
        self.assertEqual(len(FEATURE_NAMES), 22)

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
            self.assertTrue(
                self.dataset[column].between(low, high).all(),
                f"{column} outside [{low}, {high}]",
            )

    def test_binary_features_are_binary(self):
        for column in (
            "price_dropped_since_first_view",
            "payment_method_on_file",
            "is_guest_checkout",
            "is_mobile_session",
            "is_late_night_session",
            TARGET_NAME,
        ):
            self.assertTrue(set(self.dataset[column].unique()) <= {0, 1}, column)

    def test_documented_abandonment_drivers_move_in_expected_direction(self):
        """Each assertion maps to a published cart-abandonment driver."""
        data = self.dataset
        overall = data[TARGET_NAME].mean()

        def rate(mask):
            return data[mask][TARGET_NAME].mean()

        # Extra costs — the most-cited reason shoppers give.
        self.assertGreater(rate(data["delivery_fee_percent_of_cart"] > 8), overall + 0.08)
        # Basket far above this shopper's norm.
        self.assertGreater(rate(data["cart_value_vs_typical_order"] > 2.0), overall + 0.08)
        # Payment failure is a hard blocker.
        self.assertGreater(rate(data["payment_attempts_failed"] > 0), overall + 0.07)
        # Forced/absent account relationship.
        self.assertGreater(rate(data["is_guest_checkout"] == 1), overall + 0.04)
        # Slow delivery.
        self.assertGreater(rate(data["estimated_delivery_days"] > 5), overall + 0.03)
        # Commitment signals should reduce abandonment.
        self.assertLess(rate(data["checkout_steps_completed"] == 3), overall - 0.10)
        self.assertLess(rate(data["payment_method_on_file"] == 1), overall - 0.07)

    def test_bayes_column_is_a_valid_probability_and_beats_chance(self):
        from sklearn.metrics import roc_auc_score

        bayes = self.dataset[BAYES_PROBABILITY_NAME]
        self.assertTrue(bayes.between(0.0, 1.0).all())
        # The ceiling must be informative but not perfect — noise is retained.
        auc = roc_auc_score(self.dataset[TARGET_NAME], bayes)
        self.assertGreater(auc, 0.70)
        self.assertLess(auc, 0.95)


class FeatureEngineeringTests(unittest.TestCase):
    def test_output_shape_and_order(self):
        frame = generate_dataset(row_count=200, seed=3)
        engineered = engineer_features(frame[RAW_FEATURE_NAMES])
        self.assertEqual(list(engineered.columns), ALL_FEATURE_NAMES)
        self.assertEqual(len(engineered), 200)

    def test_no_target_or_oracle_can_leak_through(self):
        frame = generate_dataset(row_count=100, seed=4)
        engineered = engineer_features(frame)
        self.assertNotIn(TARGET_NAME, engineered.columns)
        self.assertNotIn(BAYES_PROBABILITY_NAME, engineered.columns)

    def test_engineered_features_are_finite(self):
        import numpy as np

        frame = generate_dataset(row_count=2_000, seed=5)
        engineered = engineer_features(frame[RAW_FEATURE_NAMES])
        self.assertTrue(np.isfinite(engineered.to_numpy()).all())


class InferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _load_artifacts()

    def test_response_contains_probability_confidence_and_all_shap_impacts(self):
        response = predict_abandonment(_sample_session())

        self.assertEqual(response.status, "success")
        self.assertGreaterEqual(response.abandonment_probability, 0)
        self.assertLessEqual(response.abandonment_probability, 1)
        self.assertAlmostEqual(
            response.confidence_score,
            abs(response.abandonment_probability - 0.5) * 2,
            places=5,
        )
        self.assertEqual(set(response.feature_impacts), set(ALL_FEATURE_NAMES))
        self.assertLessEqual(len(response.top_contributing_features), 3)
        self.assertTrue(all(item.shap_value > 0 for item in response.top_contributing_features))
        self.assertIn(response.risk_tier, {"low", "medium", "high"})

    def test_checkout_progress_reduces_predicted_risk(self):
        """Sanity check that the model learned the strongest commitment signal."""
        early = predict_abandonment(_sample_session(checkout_steps_completed=0))
        late = predict_abandonment(_sample_session(checkout_steps_completed=3))
        self.assertLess(late.abandonment_probability, early.abandonment_probability)

    def test_payment_failures_increase_predicted_risk(self):
        clean = predict_abandonment(_sample_session(payment_attempts_failed=0))
        failing = predict_abandonment(_sample_session(payment_attempts_failed=3))
        self.assertGreater(failing.abandonment_probability, clean.abandonment_probability)

    def test_saved_card_reduces_predicted_risk(self):
        guest = predict_abandonment(_sample_session(payment_method_on_file=0))
        saved = predict_abandonment(_sample_session(payment_method_on_file=1))
        self.assertLess(saved.abandonment_probability, guest.abandonment_probability)

    def test_risk_tier_matches_documented_thresholds(self):
        for probability, expected in ((0.95, "high"), (0.70, "medium"), (0.10, "low")):
            from backend.main import _risk_tier

            self.assertEqual(_risk_tier(probability), expected)


if __name__ == "__main__":
    unittest.main()
