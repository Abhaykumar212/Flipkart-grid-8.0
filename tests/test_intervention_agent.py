"""Tests for the Phase 3 intervention engine: candidates, scoring, memory,
explainability, and the orchestrator. Pure-function tests, no network — mirrors
the style of test_rca_agent.py.
"""

import unittest

from backend.agents import intervention
from backend.agents.levers import LEVER_CATALOG, LEVER_IDS, ROOT_CAUSE_CATEGORIES
from backend.agents.memory import InterventionMemoryStore
from backend.schemas import RootCauseAnalysis, ShopperProfile


def analysis_dict(
    category="cost_friction",
    confidence="high",
    recommended=None,
    avoid=None,
    contributing=None,
):
    return {
        "primary_root_cause": {
            "category": category,
            "headline": "Delivery fee pushes an already-large basket over the line",
            "explanation": "The cart is well above this shopper's usual order with a heavy delivery fee.",
            "supporting_evidence": [
                {
                    "signal": "extra_cost_burden_score",
                    "observed_value": "9% fee on a 4.9x basket",
                    "shap_contribution": 1.02,
                    "why_it_matters": "Compounded cost is the dominant driver.",
                },
                {
                    "signal": "failed_coupon_attempts",
                    "observed_value": "3",
                    "shap_contribution": 0.41,
                    "why_it_matters": "Actively hunting for a discount that never landed.",
                },
            ],
        },
        "contributing_factors": contributing or [],
        "shopper_narrative": "The shopper is hesitating over an unusually expensive basket.",
        "confidence": confidence,
        "confidence_reasoning": "Evidence concentrates on a single cost driver.",
        "recommended_levers": recommended
        if recommended is not None
        else [
            {
                "lever_id": "free_delivery_waiver",
                "rationale": "Removes the fee that dominates the attribution.",
                "expected_effect": "Directly lowers the cost barrier.",
                "priority": 1,
            },
            {
                "lever_id": "targeted_discount_code",
                "rationale": "Shopper has already attempted coupons unsuccessfully.",
                "expected_effect": "Converts an active discount-seeker.",
                "priority": 2,
            },
        ],
        "levers_to_avoid": avoid
        or [{"lever_id": "stock_scarcity_nudge", "reason": "No scarcity signal observed."}],
    }


def make_analysis(**kwargs) -> RootCauseAnalysis:
    return RootCauseAnalysis.model_validate(analysis_dict(**kwargs))


EMPTY_PROFILE = ShopperProfile()


class LeverCatalogTests(unittest.TestCase):
    def test_every_lever_has_a_headline(self):
        for lever_id in LEVER_IDS:
            self.assertIn(lever_id, intervention.LEVER_HEADLINES)

    def test_every_lever_has_a_cost_score(self):
        for meta in LEVER_CATALOG.values():
            self.assertIn(meta["cost_score"], (1, 2, 3))

    def test_every_root_cause_category_has_at_least_one_lever(self):
        for category in ROOT_CAUSE_CATEGORIES:
            matches = [m for m in LEVER_CATALOG.values() if category in m["addresses"]]
            self.assertTrue(matches, f"no lever addresses {category}")


class ContextAgentTests(unittest.TestCase):
    def test_primary_category_weighted_full(self):
        context = intervention.build_context(make_analysis(), 0.9, EMPTY_PROFILE, "s1")
        self.assertEqual(context.category_weight["cost_friction"], 1.0)

    def test_contributing_category_weighted_half(self):
        analysis = make_analysis(
            contributing=[
                {"category": "checkout_friction", "headline": "Guest checkout", "signal": "is_guest_checkout"}
            ]
        )
        context = intervention.build_context(analysis, 0.9, EMPTY_PROFILE, "s1")
        self.assertEqual(context.category_weight["checkout_friction"], 0.5)

    def test_llm_endorsement_ranked_by_priority(self):
        context = intervention.build_context(make_analysis(), 0.9, EMPTY_PROFILE, "s1")
        self.assertGreater(
            context.llm_endorsement["free_delivery_waiver"],
            context.llm_endorsement["targeted_discount_code"],
        )

    def test_levers_to_avoid_captured(self):
        context = intervention.build_context(make_analysis(), 0.9, EMPTY_PROFILE, "s1")
        self.assertIn("stock_scarcity_nudge", context.levers_to_avoid)


class CandidateAgentTests(unittest.TestCase):
    def test_category_matched_levers_included(self):
        context = intervention.build_context(make_analysis(), 0.9, EMPTY_PROFILE, "s1")
        candidates = intervention.build_candidates(context)
        self.assertIn("free_delivery_waiver", candidates)
        self.assertIn("emi_plan_highlight", candidates)  # also addresses cost_friction

    def test_avoided_lever_excluded_even_if_category_matches(self):
        analysis = make_analysis(avoid=[{"lever_id": "free_delivery_waiver", "reason": "Waivers already used."}])
        context = intervention.build_context(analysis, 0.9, EMPTY_PROFILE, "s1")
        candidates = intervention.build_candidates(context)
        self.assertNotIn("free_delivery_waiver", candidates)

    def test_unrelated_category_lever_excluded(self):
        context = intervention.build_context(make_analysis(), 0.9, EMPTY_PROFILE, "s1")
        candidates = intervention.build_candidates(context)
        # delivery_speed_upgrade only addresses delivery_friction, unrelated here
        self.assertNotIn("delivery_speed_upgrade", candidates)


class RankingAgentTests(unittest.TestCase):
    def test_primary_category_scores_higher_than_unmatched(self):
        analysis = make_analysis()
        context = intervention.build_context(analysis, 0.9, EMPTY_PROFILE, "s1")
        primary = intervention.score_candidate("free_delivery_waiver", context)
        # trust_badge_reassurance doesn't address cost_friction at all
        unrelated = intervention.score_candidate("trust_badge_reassurance", context)
        self.assertGreater(primary.score, unrelated.score)

    def test_higher_probability_increases_urgency_component(self):
        analysis = make_analysis()
        low_risk = intervention.build_context(analysis, 0.1, EMPTY_PROFILE, "s1")
        high_risk = intervention.build_context(analysis, 0.95, EMPTY_PROFILE, "s1")
        low_score = intervention.score_candidate("free_delivery_waiver", low_risk)
        high_score = intervention.score_candidate("free_delivery_waiver", high_risk)
        self.assertGreater(high_score.breakdown["urgency"], low_score.breakdown["urgency"])
        self.assertGreater(high_score.score, low_score.score)

    def test_repeated_shows_escalate_the_penalty(self):
        analysis = make_analysis()
        memory = InterventionMemoryStore(db_path=":memory:")

        once_context = intervention.build_context(analysis, 0.9, EMPTY_PROFILE, "once", memory)
        once_score = intervention.score_candidate("free_delivery_waiver", once_context).score

        memory.record("thrice", "free_delivery_waiver", "shown")
        memory.record("thrice", "free_delivery_waiver", "shown")
        memory.record("thrice", "free_delivery_waiver", "shown")
        thrice_context = intervention.build_context(analysis, 0.9, EMPTY_PROFILE, "thrice", memory)
        thrice_score = intervention.score_candidate("free_delivery_waiver", thrice_context).score

        self.assertLess(thrice_score, once_score)

    def test_dismissed_lever_is_penalised(self):
        analysis = make_analysis()
        memory = InterventionMemoryStore(db_path=":memory:")
        memory.record("s1", "free_delivery_waiver", "shown")
        memory.record("s1", "free_delivery_waiver", "dismissed")

        fresh_context = intervention.build_context(analysis, 0.9, EMPTY_PROFILE, "s2", memory)
        dismissed_context = intervention.build_context(analysis, 0.9, EMPTY_PROFILE, "s1", memory)

        fresh_score = intervention.score_candidate("free_delivery_waiver", fresh_context)
        dismissed_score = intervention.score_candidate("free_delivery_waiver", dismissed_context)
        self.assertLess(dismissed_score.score, fresh_score.score)


class ExplainabilityAgentTests(unittest.TestCase):
    def test_top_candidate_explanation_cites_shap_evidence(self):
        analysis = make_analysis()
        context = intervention.build_context(analysis, 0.9, EMPTY_PROFILE, "s1")
        candidate = intervention.score_candidate("free_delivery_waiver", context)
        trail = intervention.build_explanation(candidate, analysis, context)
        signals_cited = [f.factor for f in trail if f.factor.startswith("signal:")]
        self.assertIn("signal:extra_cost_burden_score", signals_cited)

    def test_endorsed_lever_cites_llm_rationale(self):
        analysis = make_analysis()
        context = intervention.build_context(analysis, 0.9, EMPTY_PROFILE, "s1")
        candidate = intervention.score_candidate("free_delivery_waiver", context)
        trail = intervention.build_explanation(candidate, analysis, context)
        self.assertTrue(any(f.factor == "agent_endorsement" for f in trail))


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.memory = InterventionMemoryStore(db_path=":memory:")

    def test_returns_top_three_sorted_descending(self):
        plan = intervention.build_intervention_plan(
            make_analysis(), 0.9, EMPTY_PROFILE, "s1", self.memory
        )
        self.assertEqual(len(plan.top_interventions), 3)
        scores = [item.score for item in plan.top_interventions]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_excluded_levers_never_appear_in_plan(self):
        plan = intervention.build_intervention_plan(
            make_analysis(), 0.9, EMPTY_PROFILE, "s1", self.memory
        )
        top_ids = {item.lever_id for item in plan.top_interventions}
        self.assertNotIn("stock_scarcity_nudge", top_ids)
        if plan.fallback_intervention:
            self.assertNotEqual(plan.fallback_intervention.lever_id, "stock_scarcity_nudge")

    def test_fallback_distinct_from_top_interventions(self):
        plan = intervention.build_intervention_plan(
            make_analysis(), 0.9, EMPTY_PROFILE, "s1", self.memory
        )
        top_ids = {item.lever_id for item in plan.top_interventions}
        self.assertIsNotNone(plan.fallback_intervention)
        self.assertNotIn(plan.fallback_intervention.lever_id, top_ids)

    def test_top_pick_is_llm_endorsed_when_available(self):
        plan = intervention.build_intervention_plan(
            make_analysis(), 0.9, EMPTY_PROFILE, "s1", self.memory
        )
        self.assertEqual(plan.top_interventions[0].lever_id, "free_delivery_waiver")
        self.assertTrue(plan.top_interventions[0].llm_endorsed)

    def test_marks_top_interventions_as_shown_in_memory(self):
        plan = intervention.build_intervention_plan(
            make_analysis(), 0.9, EMPTY_PROFILE, "s1", self.memory
        )
        session = self.memory.get("s1")
        for item in plan.top_interventions:
            self.assertGreaterEqual(session.shown_count(item.lever_id), 1)


class MemoryAgentTests(unittest.TestCase):
    def test_sessions_are_isolated(self):
        store = InterventionMemoryStore(db_path=":memory:")
        store.record("s1", "free_delivery_waiver", "dismissed")
        self.assertTrue(store.get("s1").was_dismissed("free_delivery_waiver"))
        self.assertFalse(store.get("s2").was_dismissed("free_delivery_waiver"))

    def test_reset_clears_single_session(self):
        store = InterventionMemoryStore(db_path=":memory:")
        store.record("s1", "free_delivery_waiver", "shown")
        store.record("s2", "free_delivery_waiver", "shown")
        store.reset("s1")
        self.assertEqual(store.get("s1").shown_count("free_delivery_waiver"), 0)
        self.assertEqual(store.get("s2").shown_count("free_delivery_waiver"), 1)


if __name__ == "__main__":
    unittest.main()
