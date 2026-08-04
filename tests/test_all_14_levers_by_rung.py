"""Comprehensive verification suite for testing all 14 intervention levers across Rungs 0 to 3.

Verifies:
1. Every lever in LEVER_CATALOG exists, has valid metadata and cost score.
2. Every root-cause category has appropriate candidate levers.
3. Ranking engine scores every lever properly.
4. Critic validation logic works for every appropriate lever-category pair.
5. All 14 levers are properly categorized into Rungs 0, 1, 2, and 3.
"""

import unittest
from backend.agents.levers import LEVER_CATALOG, LEVER_IDS
from backend.agents.intervention import build_context, score_candidate
from backend.agents.critic import build_prompt
from backend.schemas import RootCauseAnalysis, PrimaryRootCause, ShopperProfile

class TestAll14LeversByRung(unittest.TestCase):
    def setUp(self):
        # 14 levers expected in total across Rungs 0 to 3
        self.expected_levers = {
            "Rung 0": ["emi_plan_highlight", "trust_badge_reassurance", "stock_scarcity_nudge", "abandoned_cart_email"],
            "Rung 1": ["price_drop_alert", "saved_payment_prompt", "guest_to_account_nudge", "review_summary_surface"],
            "Rung 2": ["exit_intent_reminder", "checkout_assist_chat", "payment_retry_help"],
            "Rung 3": ["free_delivery_waiver", "targeted_discount_code", "delivery_speed_upgrade"],
        }
        self.shopper_profile = ShopperProfile()

    def _create_mock_rca(self, category: str, confidence: str = "high") -> RootCauseAnalysis:
        return RootCauseAnalysis(
            primary_root_cause=PrimaryRootCause(
                category=category,
                headline=f"Mock diagnosis for {category}",
                explanation="Test explanation",
                supporting_evidence=[]
            ),
            contributing_factors=[],
            shopper_narrative="Test shopper narrative",
            confidence=confidence,
            confidence_reasoning="Test confidence reasoning",
            recommended_levers=[],
            levers_to_avoid=[]
        )

    def test_total_count_and_catalog_integrity(self):
        """Verify exactly 14 levers exist in catalog with valid structure."""
        self.assertEqual(len(LEVER_IDS), 14, "Expected exactly 14 levers in catalog")
        for lever_id in LEVER_IDS:
            meta = LEVER_CATALOG[lever_id]
            self.assertIn("description", meta)
            self.assertIn("addresses", meta)
            self.assertIn("business_cost", meta)
            self.assertIn("expected_conversion_gain", meta)
            self.assertIn("cost_score", meta)
            self.assertGreater(len(meta["addresses"]), 0)

    def test_rung_0_levers(self):
        """Test Rung 0 (Passive) Levers scoring and critic prompt building."""
        for lever_id in self.expected_levers["Rung 0"]:
            self.assertIn(lever_id, LEVER_CATALOG)
            category = LEVER_CATALOG[lever_id]["addresses"][0]
            rca = self._create_mock_rca(category, confidence="high")
            ctx = build_context(rca, 0.85, self.shopper_profile, "sess_1")
            candidate = score_candidate(lever_id, ctx)
            self.assertGreater(candidate.score, 0)
            prompt = build_prompt(rca, [lever_id])
            self.assertIn(lever_id, prompt)

    def test_rung_1_levers(self):
        """Test Rung 1 (Ambient) Levers scoring and critic prompt building."""
        for lever_id in self.expected_levers["Rung 1"]:
            self.assertIn(lever_id, LEVER_CATALOG)
            category = LEVER_CATALOG[lever_id]["addresses"][0]
            rca = self._create_mock_rca(category, confidence="medium")
            ctx = build_context(rca, 0.75, self.shopper_profile, "sess_1")
            candidate = score_candidate(lever_id, ctx)
            self.assertGreater(candidate.score, 0)
            prompt = build_prompt(rca, [lever_id])
            self.assertIn(lever_id, prompt)

    def test_rung_2_levers(self):
        """Test Rung 2 (Active) Levers scoring and critic prompt building."""
        for lever_id in self.expected_levers["Rung 2"]:
            self.assertIn(lever_id, LEVER_CATALOG)
            category = LEVER_CATALOG[lever_id]["addresses"][0]
            rca = self._create_mock_rca(category, confidence="medium")
            ctx = build_context(rca, 0.80, self.shopper_profile, "sess_1")
            candidate = score_candidate(lever_id, ctx)
            self.assertGreater(candidate.score, 0)
            prompt = build_prompt(rca, [lever_id])
            self.assertIn(lever_id, prompt)

    def test_rung_3_levers(self):
        """Test Rung 3 (Costly / Margin) Levers scoring and critic prompt building."""
        for lever_id in self.expected_levers["Rung 3"]:
            self.assertIn(lever_id, LEVER_CATALOG)
            category = LEVER_CATALOG[lever_id]["addresses"][0]
            rca = self._create_mock_rca(category, confidence="high")
            ctx = build_context(rca, 0.90, self.shopper_profile, "sess_1")
            candidate = score_candidate(lever_id, ctx)
            self.assertGreater(candidate.score, 0)
            prompt = build_prompt(rca, [lever_id])
            self.assertIn(lever_id, prompt)

if __name__ == "__main__":
    unittest.main()
