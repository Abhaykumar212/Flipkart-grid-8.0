import unittest

from backend.main import SessionFeatures, _load_artifacts, predict_abandonment
from ml.feature_engineering import ALL_FEATURE_NAMES
from ml.generate_dataset import FEATURE_NAMES, generate_dataset


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = generate_dataset(row_count=6_000, seed=7)

    def test_exact_schema_and_ranges(self):
        self.assertEqual(list(self.dataset.columns), [*FEATURE_NAMES, "is_abandoned"])
        self.assertEqual(len(self.dataset), 6_000)
        self.assertTrue(self.dataset["cart_dwell_time_seconds"].between(10, 600).all())
        self.assertTrue(self.dataset["cart_pdp_bounce_count"].between(0, 10).all())
        self.assertTrue(self.dataset["reviews_expanded_count"].between(0, 8).all())
        self.assertTrue(self.dataset["cart_value_to_aov_ratio"].between(0.2, 4).all())
        self.assertTrue(self.dataset["delivery_fee_percentage"].between(0, 15).all())
        self.assertTrue(self.dataset["est_delivery_days"].between(1, 10).all())

    def test_required_non_linear_correlations(self):
        data = self.dataset
        overall = data["is_abandoned"].mean()
        price_shock = data[
            (data["cart_value_to_aov_ratio"] > 1.8)
            & (data["delivery_fee_percentage"] > 5)
        ]["is_abandoned"].mean()
        quality_uncertainty = data[
            (data["cart_pdp_bounce_count"] > 3)
            & (data["reviews_expanded_count"] > 2)
        ]["is_abandoned"].mean()
        long_delivery = data[data["est_delivery_days"] > 5]["is_abandoned"].mean()
        saved_low_value = data[
            (data["payment_method_saved"] == 1)
            & (data["cart_value_to_aov_ratio"] < 1)
        ]["is_abandoned"].mean()

        self.assertGreater(price_shock, overall + 0.15)
        self.assertGreater(quality_uncertainty, overall + 0.15)
        self.assertGreater(long_delivery, overall + 0.07)
        self.assertLess(saved_low_value, overall - 0.15)


class InferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _load_artifacts()

    def test_response_contains_probability_confidence_and_all_shap_impacts(self):
        payload = SessionFeatures(
            cart_dwell_time_seconds=420,
            cart_pdp_bounce_count=7,
            reviews_expanded_count=5,
            idle_time_before_checkout=180,
            delivery_pincode_checked=3,
            cart_value_to_aov_ratio=2.4,
            delivery_fee_percentage=9,
            est_delivery_days=7,
            has_price_dropped_recently=0,
            hist_abandonment_rate=0.75,
            discount_sensitivity_score=0.8,
            past_return_rate=0.2,
            wishlist_item_count=2,
            payment_method_saved=0,
        )
        response = predict_abandonment(payload)

        self.assertEqual(response.status, "success")
        self.assertGreaterEqual(response.abandonment_probability, 0)
        self.assertLessEqual(response.abandonment_probability, 1)
        self.assertAlmostEqual(
            response.confidence_score,
            abs(response.abandonment_probability - 0.5) * 2,
            places=5,
        )
        # Model now uses 22 features (14 raw + 8 engineered)
        self.assertEqual(set(response.feature_impacts), set(ALL_FEATURE_NAMES))
        self.assertLessEqual(len(response.top_contributing_features), 3)
        self.assertTrue(all(item.shap_value > 0 for item in response.top_contributing_features))


if __name__ == "__main__":
    unittest.main()
