"""Tests for the Phase 2 root-cause agent: gate policy, prompt, schema, tracing.

The LLM call itself is not exercised here — network behaviour is covered by the
separate live smoke test. What matters in CI is that the gate spends budget
correctly and that malformed model output is rejected rather than propagated to
the next phase.
"""

import unittest

from backend import config
from backend.agents import gate, root_cause
from backend.agents.levers import LEVER_CATALOG, LEVER_IDS, ROOT_CAUSE_CATEGORIES
from backend.schemas import CartContext, CartLine, RootCauseAnalysis
from backend.trace import Stage, Status, TraceRecorder


def sample_features(**overrides):
    base = {
        "seconds_spent_in_cart": 420.0,
        "times_returned_to_product_page": 4,
        "product_reviews_read": 5,
        "seconds_idle_before_checkout": 180.0,
        "delivery_pincode_checks": 3,
        "saved_items_in_wishlist": 2,
        "cart_value_vs_typical_order": 4.9,
        "delivery_fee_percent_of_cart": 9.0,
        "price_dropped_since_first_view": 0,
        "discount_seeking_tendency": 0.85,
        "failed_coupon_attempts": 3,
        "estimated_delivery_days": 8,
        "payment_method_on_file": 0,
        "checkout_steps_completed": 0,
        "payment_attempts_failed": 0,
        "is_guest_checkout": 1,
        "past_abandonment_rate": 0.72,
        "past_order_return_rate": 0.15,
        "lifetime_orders_placed": 2,
        "days_since_last_purchase": 210.0,
        "is_mobile_session": 1,
        "is_late_night_session": 1,
    }
    base.update(overrides)
    return base


def valid_analysis_dict():
    return {
        "primary_root_cause": {
            "category": "cost_friction",
            "headline": "Delivery fee pushes an already-large basket over the line",
            "explanation": "The cart is 4.9x this shopper's usual order and carries a 9% delivery fee.",
            "supporting_evidence": [
                {
                    "signal": "extra_cost_burden_score",
                    "observed_value": "9% fee on a 4.9x basket",
                    "shap_contribution": 1.02,
                    "why_it_matters": "Compounded cost is the dominant driver.",
                }
            ],
        },
        "contributing_factors": [
            {
                "category": "checkout_friction",
                "headline": "No checkout steps completed",
                "signal": "checkout_steps_completed",
            }
        ],
        "shopper_narrative": "The shopper is hesitating over an unusually expensive basket.",
        "confidence": "high",
        "confidence_reasoning": "Evidence concentrates on a single cost driver.",
        "recommended_levers": [
            {
                "lever_id": "free_delivery_waiver",
                "rationale": "Removes the fee that dominates the attribution.",
                "expected_effect": "Directly lowers the cost barrier.",
                "priority": 1,
            }
        ],
        "levers_to_avoid": [
            {"lever_id": "price_drop_alert", "reason": "No price drop has occurred."}
        ],
    }


class GatePolicyTests(unittest.TestCase):
    def setUp(self):
        self.store = gate.GateStore()

    def test_fires_at_or_above_threshold(self):
        result = gate.evaluate(0.94, 400, "sig-a", "s1", self.store)
        self.assertTrue(result.fired)
        self.assertEqual(result.threshold, config.RCA_PROBABILITY_THRESHOLD)

    def test_does_not_fire_below_threshold(self):
        result = gate.evaluate(0.79, 400, "sig-a", "s1", self.store)
        self.assertFalse(result.fired)
        self.assertIn("below", result.reason)

    def test_exact_threshold_boundary_fires(self):
        result = gate.evaluate(config.RCA_PROBABILITY_THRESHOLD, 400, "sig-a", "s1", self.store)
        self.assertTrue(result.fired)

    def test_waits_for_cart_warmup(self):
        result = gate.evaluate(0.95, 3, "sig-a", "s1", self.store)
        self.assertFalse(result.fired)
        self.assertIn("old", result.reason)

    def test_identical_signature_within_cooldown_is_suppressed(self):
        self.store.record_run("s1", "sig-a", at=1000.0)
        result = gate.evaluate(0.95, 400, "sig-a", "s1", self.store, now=1010.0)
        self.assertFalse(result.fired)
        self.assertIn("unchanged", result.reason)

    def test_changed_signature_refires_immediately(self):
        self.store.record_run("s1", "sig-a", at=1000.0)
        result = gate.evaluate(0.95, 400, "sig-DIFFERENT", "s1", self.store, now=1010.0)
        self.assertTrue(result.fired)
        self.assertIn("changed", result.reason)

    def test_cooldown_expiry_allows_refire(self):
        self.store.record_run("s1", "sig-a", at=1000.0)
        later = 1000.0 + config.RCA_COOLDOWN_SECONDS + 1
        result = gate.evaluate(0.95, 400, "sig-a", "s1", self.store, now=later)
        self.assertTrue(result.fired)

    def test_session_budget_is_enforced(self):
        for _ in range(config.RCA_MAX_PER_SESSION):
            self.store.record_run("s1", "sig-x")
        result = gate.evaluate(0.99, 400, "sig-new", "s1", self.store)
        self.assertFalse(result.fired)
        self.assertIn("budget", result.reason)

    def test_force_bypasses_cooldown_but_not_budget(self):
        self.store.record_run("s1", "sig-a", at=1000.0)
        forced = gate.evaluate(0.95, 400, "sig-a", "s1", self.store, force=True, now=1001.0)
        self.assertTrue(forced.fired)

        for _ in range(config.RCA_MAX_PER_SESSION):
            self.store.record_run("s2", "sig-a")
        capped = gate.evaluate(0.95, 400, "sig-a", "s2", self.store, force=True)
        self.assertFalse(capped.fired, "force must not bypass the hard session cap")

    def test_force_ignores_low_probability(self):
        """Manual re-run is for demos and debugging, so it should still work."""
        result = gate.evaluate(0.05, 400, "sig-a", "s1", self.store, force=True)
        self.assertTrue(result.fired)

    def test_sessions_are_isolated(self):
        self.store.record_run("s1", "sig-a", at=1000.0)
        other = gate.evaluate(0.95, 400, "sig-a", "s2", self.store, now=1001.0)
        self.assertTrue(other.fired)


class FeatureSignatureTests(unittest.TestCase):
    def test_signature_is_stable(self):
        a = root_cause.build_feature_signature(sample_features())
        b = root_cause.build_feature_signature(sample_features())
        self.assertEqual(a, b)

    def test_material_change_alters_signature(self):
        base = root_cause.build_feature_signature(sample_features())
        changed = root_cause.build_feature_signature(
            sample_features(payment_attempts_failed=3)
        )
        self.assertNotEqual(base, changed)

    def test_immaterial_drift_does_not_alter_signature(self):
        """Dwell time ticks up constantly; it must not re-trigger the agent."""
        base = root_cause.build_feature_signature(sample_features())
        drifted = root_cause.build_feature_signature(
            sample_features(seconds_spent_in_cart=431.0, seconds_idle_before_checkout=194.0)
        )
        self.assertEqual(base, drifted)


class EvidenceAndPromptTests(unittest.TestCase):
    def setUp(self):
        self.features = sample_features()
        self.impacts = {
            "cart_value_vs_typical_order": 0.99,
            "delivery_fee_percent_of_cart": 0.62,
            # Funnel-progress features: excluded from evidence by design (see
            # DIAGNOSTIC_FEATURE_NAMES), even though they dwarf everything
            # else here in magnitude. Several tests below assert they never
            # surface in build_evidence's output.
            "checkout_steps_completed": 5.0,
            "payment_method_on_file": -4.5,
            "estimated_delivery_days": 0.31,
            "price_dropped_since_first_view": -0.20,
        }
        self.cart = CartContext(
            lines=[
                CartLine(
                    product_id="p-1001",
                    title="Apple iPhone 16",
                    brand="Apple",
                    quantity=1,
                    selling_price=71999,
                    mrp=79900,
                    discount_percent=10,
                    estimated_delivery_days=8,
                )
            ],
            cart_total=71999,
            mrp_total=79900,
            delivery_fee=6480,
            cart_age_seconds=420,
        )

    def test_evidence_is_ranked_by_absolute_shap(self):
        evidence = root_cause.build_evidence(self.features, self.impacts)
        magnitudes = [abs(item["shap_contribution"]) for item in evidence]
        self.assertEqual(magnitudes, sorted(magnitudes, reverse=True))

    def test_evidence_includes_protective_signals(self):
        """Negative SHAP matters too — it tells the agent what is holding them in."""
        evidence = root_cause.build_evidence(self.features, self.impacts)
        directions = {item["direction"] for item in evidence}
        self.assertIn("reduces abandonment risk", directions)

    def test_evidence_carries_human_labels_and_values(self):
        evidence = root_cause.build_evidence(self.features, self.impacts)
        top = evidence[0]
        self.assertEqual(top["signal"], "cart_value_vs_typical_order")
        self.assertIn("4.90x", top["observed_value"])
        self.assertNotEqual(top["label"], top["signal"], "label should be human readable")

    def test_evidence_excludes_funnel_progress_even_when_dominant(self):
        """checkout_steps_completed/payment_method_on_file dwarf everything
        else in self.impacts, but they measure how far along the funnel a
        shopper got, not why — they must never surface as diagnosis evidence.
        """
        evidence = root_cause.build_evidence(self.features, self.impacts)
        signals = {item["signal"] for item in evidence}
        self.assertNotIn("checkout_steps_completed", signals)
        self.assertNotIn("payment_method_on_file", signals)

    def test_diagnostic_feature_names_exclude_funnel_progress(self):
        self.assertNotIn("checkout_steps_completed", root_cause.DIAGNOSTIC_FEATURE_NAMES)
        self.assertNotIn("checkout_progress_ratio", root_cause.DIAGNOSTIC_FEATURE_NAMES)
        self.assertNotIn("payment_method_on_file", root_cause.DIAGNOSTIC_FEATURE_NAMES)

    def test_prompt_contains_the_grounding_the_agent_needs(self):
        evidence = root_cause.build_evidence(self.features, self.impacts)
        prompt = root_cause.build_prompt(0.94, "high", 0.88, self.features, evidence, self.cart)

        self.assertIn("SHAP ATTRIBUTION", prompt)
        self.assertIn("cart_value_vs_typical_order", prompt)
        self.assertIn("Apple iPhone 16", prompt)
        self.assertIn("free_delivery_waiver", prompt, "lever catalog must be offered")
        for category in ROOT_CAUSE_CATEGORIES:
            self.assertIn(category, prompt)

    def test_prompt_never_contains_the_api_key(self):
        evidence = root_cause.build_evidence(self.features, self.impacts)
        prompt = root_cause.build_prompt(0.94, "high", 0.88, self.features, evidence, self.cart)
        self.assertNotIn("gsk_", prompt)


class ResponseSchemaTests(unittest.TestCase):
    def test_valid_payload_parses(self):
        analysis = RootCauseAnalysis.model_validate(valid_analysis_dict())
        self.assertEqual(analysis.primary_root_cause.category, "cost_friction")
        self.assertEqual(analysis.recommended_levers[0].lever_id, "free_delivery_waiver")

    def test_unknown_lever_is_rejected(self):
        payload = valid_analysis_dict()
        payload["recommended_levers"][0]["lever_id"] = "send_carrier_pigeon"
        with self.assertRaises(Exception):
            RootCauseAnalysis.model_validate(payload)

    def test_unknown_category_is_rejected(self):
        payload = valid_analysis_dict()
        payload["primary_root_cause"]["category"] = "vibes"
        with self.assertRaises(Exception):
            RootCauseAnalysis.model_validate(payload)

    def test_missing_required_section_is_rejected(self):
        payload = valid_analysis_dict()
        del payload["shopper_narrative"]
        with self.assertRaises(Exception):
            RootCauseAnalysis.model_validate(payload)

    def test_groq_schema_is_strict_everywhere(self):
        """Groq strict mode requires additionalProperties:false on every object."""

        def assert_strict(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(
                        node.get("additionalProperties"),
                        False,
                        f"object missing additionalProperties:false: {list(node.get('properties', {}))}",
                    )
                for value in node.values():
                    assert_strict(value)
            elif isinstance(node, list):
                for value in node:
                    assert_strict(value)

        assert_strict(root_cause._response_schema())

    def test_schema_enums_match_the_catalog(self):
        schema = root_cause._response_schema()
        lever_enum = schema["properties"]["recommended_levers"]["items"]["properties"]["lever_id"]["enum"]
        self.assertEqual(set(lever_enum), set(LEVER_IDS))


class LeverCatalogTests(unittest.TestCase):
    def test_every_lever_addresses_a_known_category(self):
        for lever_id, meta in LEVER_CATALOG.items():
            for category in meta["addresses"]:
                self.assertIn(category, ROOT_CAUSE_CATEGORIES, f"{lever_id} -> {category}")

    def test_every_category_has_at_least_one_lever(self):
        """Otherwise the agent could diagnose a cause it cannot act on."""
        covered = {c for meta in LEVER_CATALOG.values() for c in meta["addresses"]}
        for category in ROOT_CAUSE_CATEGORIES:
            self.assertIn(category, covered, f"no lever addresses {category}")


class TraceTests(unittest.TestCase):
    def test_span_records_duration_and_detail(self):
        recorder = TraceRecorder()
        with recorder.span(Stage.MODEL_INFERENCE, "test") as span:
            span["detail"] = {"probability": 0.9}
        self.assertEqual(len(recorder.spans), 1)
        self.assertEqual(recorder.spans[0]["status"], Status.OK)
        self.assertEqual(recorder.spans[0]["detail"]["probability"], 0.9)
        self.assertEqual(recorder.spans[0]["source"], "backend")

    def test_span_marks_error_and_reraises(self):
        recorder = TraceRecorder()
        with self.assertRaises(ValueError):
            with recorder.span(Stage.ROOT_CAUSE_AGENT, "boom"):
                raise ValueError("kaboom")
        self.assertEqual(recorder.spans[0]["status"], Status.ERROR)
        self.assertIn("kaboom", recorder.spans[0]["detail"]["error"])

    def test_run_ids_are_unique(self):
        self.assertNotEqual(TraceRecorder().run_id, TraceRecorder().run_id)


class ConfigTests(unittest.TestCase):
    def test_redacted_key_hint_never_exposes_the_key(self):
        hint = config.redacted_key_hint()
        if config.GROQ_API_KEY:
            self.assertNotIn(config.GROQ_API_KEY, hint)
            self.assertIn("…", hint)
        else:
            self.assertEqual(hint, "not-set")

    def test_token_budget_is_high_enough_for_the_schema(self):
        """Below ~1500 the reasoning budget is consumed before JSON is emitted."""
        self.assertGreaterEqual(config.RCA_MAX_TOKENS, 1500)

    def test_threshold_matches_the_high_risk_tier(self):
        from backend.main import _risk_tier

        self.assertEqual(_risk_tier(config.RCA_PROBABILITY_THRESHOLD), "high")


if __name__ == "__main__":
    unittest.main()
