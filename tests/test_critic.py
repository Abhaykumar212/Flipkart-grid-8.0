"""Tests for the critic gate: skip path, downgrade, total rejection, fail-open.

The LLM call is faked throughout — what matters here is which branch `review`
takes and what it does with the verdicts, not that a provider answers. The fake
also asserts the negative case the skip path exists for: that no call is made at
all when the ranking already agrees with the diagnosis.
"""

import unittest
from unittest import mock

from backend import config
from backend.agents import critic
from backend.schemas import InterventionPlan, RecommendedIntervention, RootCauseAnalysis
from backend.trace import Stage, Status, TraceRecorder


def analysis(category="product_uncertainty", confidence="medium") -> RootCauseAnalysis:
    return RootCauseAnalysis.model_validate(
        {
            "primary_root_cause": {
                "category": category,
                "headline": "Shopper is still comparing before committing",
                "explanation": "Four returns to the product page and five reviews read.",
                "supporting_evidence": [
                    {
                        "signal": "times_returned_to_product_page",
                        "observed_value": "4",
                        "shap_contribution": 0.82,
                        "why_it_matters": "Repeat research without adding to cart.",
                    }
                ],
            },
            "contributing_factors": [],
            "shopper_narrative": "Still deciding whether this is the right product.",
            "confidence": confidence,
            "confidence_reasoning": "Evidence concentrates on research behaviour.",
            "recommended_levers": [
                {
                    "lever_id": "review_summary_surface",
                    "rationale": "Resolves the doubt without more research.",
                    "expected_effect": "Shortens the comparison loop.",
                    "priority": 1,
                }
            ],
            "levers_to_avoid": [],
        }
    )


def lever(lever_id: str, score: float) -> RecommendedIntervention:
    return RecommendedIntervention(
        lever_id=lever_id,
        headline="headline",
        rationale="rationale",
        score=score,
        confidence="medium",
        expected_conversion_gain=0.2,
        business_cost="low",
        llm_endorsed=True,
    )


def plan(*levers: RecommendedIntervention) -> InterventionPlan:
    return InterventionPlan(top_interventions=list(levers), fallback_intervention=None)


def verdicts(*pairs) -> dict:
    return {
        "verdicts": [
            {
                "lever_id": lever_id,
                "aligned": alignment >= 0.5,
                "alignment": alignment,
                "reasoning": f"{lever_id} scored {alignment}",
            }
            for lever_id, alignment in pairs
        ]
    }


def spans_for(recorder: TraceRecorder, stage: str):
    return [span for span in recorder.spans if span["stage"] == stage]


class SkipPathTests(unittest.TestCase):
    def test_high_confidence_and_high_score_makes_no_call(self):
        recorder = TraceRecorder()
        with mock.patch.object(critic, "call_critic") as call:
            verdict = critic.review(
                analysis(confidence="high"),
                plan(lever("review_summary_surface", config.CRITIC_SKIP_SCORE + 0.5)),
                recorder,
            )
        call.assert_not_called()
        self.assertEqual(verdict.path, critic.PATH_SKIPPED)
        self.assertEqual(verdict.approved_lever_id, "review_summary_surface")

    def test_high_score_on_a_shaky_diagnosis_still_calls(self):
        """The case the critic exists for — a decisive lever on a diffuse cause."""
        recorder = TraceRecorder()
        with mock.patch.object(
            critic,
            "call_critic",
            return_value=(verdicts(("review_summary_surface", 0.9)), {}),
        ) as call:
            verdict = critic.review(
                analysis(confidence="low"),
                plan(lever("review_summary_surface", config.CRITIC_SKIP_SCORE + 5)),
                recorder,
            )
        call.assert_called_once()
        self.assertEqual(verdict.path, critic.PATH_LLM)

    def test_confident_diagnosis_with_a_narrow_win_still_calls(self):
        recorder = TraceRecorder()
        with mock.patch.object(
            critic,
            "call_critic",
            return_value=(verdicts(("review_summary_surface", 0.8)), {}),
        ) as call:
            critic.review(
                analysis(confidence="high"),
                plan(lever("review_summary_surface", config.CRITIC_SKIP_SCORE - 0.1)),
                recorder,
            )
        call.assert_called_once()

    def test_skip_is_recorded_as_a_skipped_span(self):
        recorder = TraceRecorder()
        with mock.patch.object(critic, "call_critic"):
            critic.review(
                analysis(confidence="high"),
                plan(lever("review_summary_surface", 99.0)),
                recorder,
            )
        span = spans_for(recorder, Stage.CRITIC_VERDICT)[0]
        self.assertEqual(span["status"], Status.SKIPPED)
        self.assertFalse(span["detail"]["llm_call"])


class DowngradeTests(unittest.TestCase):
    def setUp(self):
        self.recorder = TraceRecorder()
        self.plan = plan(
            lever("targeted_discount_code", 6.0),
            lever("review_summary_surface", 5.5),
            lever("stock_scarcity_nudge", 5.0),
        )

    def test_failing_top_pick_downgrades_to_the_next_ranked(self):
        with mock.patch.object(
            critic,
            "call_critic",
            return_value=(
                verdicts(
                    ("targeted_discount_code", 0.1),
                    ("review_summary_surface", 0.95),
                    ("stock_scarcity_nudge", 0.6),
                ),
                {},
            ),
        ):
            verdict = critic.review(analysis(), self.plan, self.recorder)

        self.assertEqual(verdict.approved_lever_id, "review_summary_surface")
        self.assertEqual([lever_id for lever_id, _ in verdict.rejected], ["targeted_discount_code"])

    def test_levers_below_the_approved_one_are_never_rejected(self):
        """Only what outranked the approved lever was actually passed over."""
        with mock.patch.object(
            critic,
            "call_critic",
            return_value=(
                verdicts(
                    ("targeted_discount_code", 0.9),
                    ("review_summary_surface", 0.0),
                    ("stock_scarcity_nudge", 0.0),
                ),
                {},
            ),
        ):
            verdict = critic.review(analysis(), self.plan, self.recorder)

        self.assertEqual(verdict.approved_lever_id, "targeted_discount_code")
        self.assertEqual(verdict.rejected, [])

    def test_nothing_passing_approves_nothing(self):
        with mock.patch.object(
            critic,
            "call_critic",
            return_value=(
                verdicts(
                    ("targeted_discount_code", 0.2),
                    ("review_summary_surface", 0.1),
                    ("stock_scarcity_nudge", 0.0),
                ),
                {},
            ),
        ):
            verdict = critic.review(analysis(), self.plan, self.recorder)

        self.assertIsNone(verdict.approved_lever_id)
        self.assertEqual(len(verdict.rejected), 3)

    def test_a_lever_the_critic_ignored_is_treated_as_passing(self):
        """A dropped verdict must not silence a lever nobody judged."""
        with mock.patch.object(
            critic, "call_critic", return_value=(verdicts(("targeted_discount_code", 0.0)), {})
        ):
            verdict = critic.review(analysis(), self.plan, self.recorder)
        self.assertEqual(verdict.approved_lever_id, "review_summary_surface")

    def test_threshold_boundary_passes(self):
        with mock.patch.object(
            critic,
            "call_critic",
            return_value=(verdicts(("targeted_discount_code", config.CRITIC_PASS_THRESHOLD)), {}),
        ):
            verdict = critic.review(analysis(), self.plan, self.recorder)
        self.assertEqual(verdict.approved_lever_id, "targeted_discount_code")

    def test_span_reports_the_downgrade(self):
        with mock.patch.object(
            critic,
            "call_critic",
            return_value=(
                verdicts(("targeted_discount_code", 0.1), ("review_summary_surface", 0.9)),
                {},
            ),
        ):
            critic.review(analysis(), self.plan, self.recorder)

        span = spans_for(self.recorder, Stage.CRITIC_VERDICT)[0]
        self.assertIn("targeted_discount_code -> review_summary_surface", span["label"])
        self.assertEqual(span["detail"]["approved_lever_id"], "review_summary_surface")
        self.assertEqual(span["detail"]["rejected"][0]["lever_id"], "targeted_discount_code")


class FailOpenTests(unittest.TestCase):
    def test_rate_limit_approves_the_top_pick_unreviewed(self):
        recorder = TraceRecorder()
        with mock.patch.object(
            critic, "call_critic", side_effect=critic.RateLimitedError("quota")
        ):
            verdict = critic.review(
                analysis(), plan(lever("targeted_discount_code", 6.0)), recorder
            )

        self.assertEqual(verdict.path, critic.PATH_UNAVAILABLE)
        self.assertEqual(verdict.approved_lever_id, "targeted_discount_code")
        self.assertEqual(spans_for(recorder, Stage.CRITIC_VERDICT)[0]["status"], Status.RATE_LIMITED)

    def test_provider_error_also_fails_open(self):
        recorder = TraceRecorder()
        with mock.patch.object(critic, "call_critic", side_effect=RuntimeError("boom")):
            verdict = critic.review(
                analysis(), plan(lever("targeted_discount_code", 6.0)), recorder
            )

        self.assertEqual(verdict.approved_lever_id, "targeted_discount_code")
        self.assertEqual(spans_for(recorder, Stage.CRITIC_VERDICT)[0]["status"], Status.ERROR)

    def test_disabled_critic_approves_without_calling(self):
        recorder = TraceRecorder()
        with mock.patch.object(config, "CRITIC_ENABLED", False), mock.patch.object(
            critic, "call_critic"
        ) as call:
            verdict = critic.review(
                analysis(), plan(lever("targeted_discount_code", 0.5)), recorder
            )
        call.assert_not_called()
        self.assertEqual(verdict.path, critic.PATH_DISABLED)


class PromptAndSchemaTests(unittest.TestCase):
    def test_prompt_carries_the_cause_and_each_lever_purpose(self):
        prompt = critic.build_prompt(
            analysis(), ["review_summary_surface", "targeted_discount_code"]
        )
        self.assertIn("product_uncertainty", prompt)
        self.assertIn("Shopper is still comparing", prompt)
        self.assertIn("review_summary_surface", prompt)
        # The lever's declared categories are what alignment is judged against.
        self.assertIn("Designed for:", prompt)

    def test_schema_is_strict_and_closed(self):
        schema = critic._response_schema()
        item = schema["properties"]["verdicts"]["items"]
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(item["additionalProperties"])
        self.assertEqual(
            set(item["required"]), {"lever_id", "aligned", "alignment", "reasoning"}
        )

    def test_lever_ids_are_constrained_to_the_catalog(self):
        item = critic._response_schema()["properties"]["verdicts"]["items"]
        self.assertIn("review_summary_surface", item["properties"]["lever_id"]["enum"])
        self.assertNotIn("invented_lever", item["properties"]["lever_id"]["enum"])


if __name__ == "__main__":
    unittest.main()
