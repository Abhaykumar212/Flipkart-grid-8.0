"""Tests for the explanation grounding scorer: grounded, regenerate, template
fallback, fail-open, disabled.

The LLM calls are faked throughout, mirroring tests/test_critic.py — what
matters here is which branch `score` takes, whether it mutates the explanation,
and that it never spends more than one scoring call plus one regenerate call.
"""

import unittest
from unittest import mock

from backend import config
from backend.agents import explanation_scorer
from backend.agents.root_cause import RateLimitedError
from backend.schemas import RootCauseAnalysis
from backend.trace import Stage, Status, TraceRecorder


def analysis(confidence="medium") -> RootCauseAnalysis:
    return RootCauseAnalysis.model_validate(
        {
            "primary_root_cause": {
                "category": "product_uncertainty",
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


def evidence_list():
    return [
        {
            "signal": "times_returned_to_product_page",
            "label": "Times returned to product page",
            "observed_value": "4",
            "shap_contribution": 0.82,
            "direction": "increases abandonment risk",
        },
        {
            "signal": "product_reviews_read",
            "label": "Product reviews read",
            "observed_value": "5",
            "shap_contribution": 0.41,
            "direction": "increases abandonment risk",
        },
    ]


def spans_for(recorder: TraceRecorder, stage: str):
    return [span for span in recorder.spans if span["stage"] == stage]


class GroundedPathTests(unittest.TestCase):
    def test_no_unsupported_claims_is_grounded_and_leaves_explanation_untouched(self):
        recorder = TraceRecorder()
        case = analysis()
        original_text = case.primary_root_cause.explanation
        with mock.patch.object(
            explanation_scorer,
            "call_scorer",
            return_value=({"grounded": True, "unsupported_claims": [], "confidence": 0.9}, {}),
        ) as call, mock.patch.object(explanation_scorer, "call_regenerate") as regen:
            result = explanation_scorer.score(case, evidence_list(), recorder)

        call.assert_called_once()
        regen.assert_not_called()
        self.assertEqual(result.verdict, explanation_scorer.VERDICT_GROUNDED)
        self.assertEqual(case.primary_root_cause.explanation, original_text)
        spans = spans_for(recorder, Stage.EXPLANATION_SCORED)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["status"], Status.OK)
        self.assertEqual(spans[0]["detail"]["verdict"], explanation_scorer.VERDICT_GROUNDED)


class RegenerateTests(unittest.TestCase):
    def test_unsupported_claim_triggers_one_regenerate_call_and_mutates_explanation(self):
        recorder = TraceRecorder()
        case = analysis()
        new_text = (
            "The shopper returned to the product page 4 times "
            "(times_returned_to_product_page), which increases abandonment risk."
        )
        with mock.patch.object(
            explanation_scorer,
            "call_scorer",
            return_value=(
                {
                    "grounded": False,
                    "unsupported_claims": ["shopper seems hesitant for unstated reasons"],
                    "confidence": 0.7,
                },
                {},
            ),
        ), mock.patch.object(
            explanation_scorer, "call_regenerate", return_value=({"explanation": new_text}, {})
        ) as regen:
            result = explanation_scorer.score(case, evidence_list(), recorder)

        regen.assert_called_once()
        self.assertEqual(result.verdict, explanation_scorer.VERDICT_REGENERATED)
        self.assertEqual(case.primary_root_cause.explanation, new_text)
        spans = spans_for(recorder, Stage.EXPLANATION_SCORED)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["detail"]["verdict"], explanation_scorer.VERDICT_REGENERATED)


class TemplateFallbackTests(unittest.TestCase):
    def _score_with_unsupported_claim(self, recorder, case):
        return mock.patch.object(
            explanation_scorer,
            "call_scorer",
            return_value=(
                {"grounded": False, "unsupported_claims": ["an invented claim"], "confidence": 0.5},
                {},
            ),
        )

    def test_rewrite_that_still_fails_verification_falls_back_to_template(self):
        recorder = TraceRecorder()
        case = analysis()
        ungrounded_rewrite = "Shoppers generally hesitate for various unspecified reasons."
        with self._score_with_unsupported_claim(recorder, case), mock.patch.object(
            explanation_scorer,
            "call_regenerate",
            return_value=({"explanation": ungrounded_rewrite}, {}),
        ):
            result = explanation_scorer.score(case, evidence_list(), recorder)

        self.assertEqual(result.verdict, explanation_scorer.VERDICT_TEMPLATE_FALLBACK)
        self.assertNotEqual(case.primary_root_cause.explanation, ungrounded_rewrite)
        spans = spans_for(recorder, Stage.EXPLANATION_SCORED)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["status"], Status.OK)
        self.assertEqual(spans[0]["detail"]["verdict"], explanation_scorer.VERDICT_TEMPLATE_FALLBACK)

    def test_regenerate_provider_error_falls_back_to_template(self):
        recorder = TraceRecorder()
        case = analysis()
        with self._score_with_unsupported_claim(recorder, case), mock.patch.object(
            explanation_scorer, "call_regenerate", side_effect=RuntimeError("boom")
        ):
            result = explanation_scorer.score(case, evidence_list(), recorder)

        self.assertEqual(result.verdict, explanation_scorer.VERDICT_TEMPLATE_FALLBACK)
        spans = spans_for(recorder, Stage.EXPLANATION_SCORED)
        self.assertEqual(spans[0]["status"], Status.ERROR)

    def test_regenerate_rate_limit_falls_back_to_template(self):
        recorder = TraceRecorder()
        case = analysis()
        with self._score_with_unsupported_claim(recorder, case), mock.patch.object(
            explanation_scorer, "call_regenerate", side_effect=RateLimitedError("quota")
        ):
            result = explanation_scorer.score(case, evidence_list(), recorder)

        self.assertEqual(result.verdict, explanation_scorer.VERDICT_TEMPLATE_FALLBACK)
        spans = spans_for(recorder, Stage.EXPLANATION_SCORED)
        self.assertEqual(spans[0]["status"], Status.RATE_LIMITED)


class FailOpenTests(unittest.TestCase):
    def test_rate_limit_on_first_call_is_trusted_as_grounded(self):
        recorder = TraceRecorder()
        case = analysis()
        original_text = case.primary_root_cause.explanation
        with mock.patch.object(
            explanation_scorer, "call_scorer", side_effect=RateLimitedError("quota")
        ), mock.patch.object(explanation_scorer, "call_regenerate") as regen:
            result = explanation_scorer.score(case, evidence_list(), recorder)

        regen.assert_not_called()
        self.assertEqual(result.path, explanation_scorer.PATH_UNAVAILABLE)
        self.assertEqual(result.verdict, explanation_scorer.VERDICT_GROUNDED)
        self.assertEqual(case.primary_root_cause.explanation, original_text)
        self.assertEqual(spans_for(recorder, Stage.EXPLANATION_SCORED)[0]["status"], Status.RATE_LIMITED)

    def test_provider_error_on_first_call_also_fails_open(self):
        recorder = TraceRecorder()
        case = analysis()
        with mock.patch.object(explanation_scorer, "call_scorer", side_effect=RuntimeError("boom")):
            result = explanation_scorer.score(case, evidence_list(), recorder)

        self.assertEqual(result.verdict, explanation_scorer.VERDICT_GROUNDED)
        self.assertEqual(spans_for(recorder, Stage.EXPLANATION_SCORED)[0]["status"], Status.ERROR)


class DisabledPathTests(unittest.TestCase):
    def test_disabled_scorer_never_calls_and_returns_no_verdict(self):
        recorder = TraceRecorder()
        case = analysis()
        with mock.patch.object(config, "EXPLANATION_SCORER_ENABLED", False), mock.patch.object(
            explanation_scorer, "call_scorer"
        ) as call:
            result = explanation_scorer.score(case, evidence_list(), recorder)

        call.assert_not_called()
        self.assertIsNone(result.verdict)
        self.assertEqual(result.path, explanation_scorer.PATH_DISABLED)
        self.assertEqual(spans_for(recorder, Stage.EXPLANATION_SCORED)[0]["status"], Status.SKIPPED)


class PromptAndSchemaTests(unittest.TestCase):
    def test_prompt_carries_evidence_and_every_justification_field(self):
        case = analysis()
        prompt = explanation_scorer.build_prompt(case, evidence_list())
        self.assertIn("times_returned_to_product_page", prompt)
        self.assertIn(case.primary_root_cause.explanation, prompt)
        self.assertIn("Repeat research without adding to cart.", prompt)
        self.assertIn(case.confidence_reasoning, prompt)
        self.assertIn("Resolves the doubt without more research.", prompt)

    def test_regenerate_prompt_carries_flagged_claims_and_evidence(self):
        case = analysis()
        prompt = explanation_scorer.build_regenerate_prompt(
            case, evidence_list(), ["an invented claim"]
        )
        self.assertIn("an invented claim", prompt)
        self.assertIn("times_returned_to_product_page", prompt)

    def test_score_schema_is_strict_and_closed(self):
        schema = explanation_scorer._score_response_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["required"]), {"grounded", "unsupported_claims", "confidence"}
        )

    def test_regenerate_schema_is_strict_and_closed(self):
        schema = explanation_scorer._regenerate_response_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), {"explanation"})


class VerifyHelperTests(unittest.TestCase):
    def test_text_quoting_a_signal_name_is_grounded(self):
        text = "This cites times_returned_to_product_page directly."
        self.assertTrue(explanation_scorer._verify_grounded_text(text, evidence_list()))

    def test_text_quoting_a_label_is_grounded(self):
        text = "Times returned to product page was the key driver."
        self.assertTrue(explanation_scorer._verify_grounded_text(text, evidence_list()))

    def test_text_quoting_an_observed_value_context_is_grounded(self):
        text = "The shopper did this 4 times before hesitating."
        self.assertTrue(explanation_scorer._verify_grounded_text(text, evidence_list()))

    def test_text_with_no_evidence_reference_is_not_grounded(self):
        text = "Shoppers generally hesitate for various unspecified reasons."
        self.assertFalse(explanation_scorer._verify_grounded_text(text, evidence_list()))

    def test_empty_text_is_not_grounded(self):
        self.assertFalse(explanation_scorer._verify_grounded_text("", evidence_list()))

    def test_case_insensitive_match(self):
        text = "TIMES_RETURNED_TO_PRODUCT_PAGE was the dominant signal."
        self.assertTrue(explanation_scorer._verify_grounded_text(text, evidence_list()))


class TemplateHelperTests(unittest.TestCase):
    def test_empty_evidence_returns_generic_fallback(self):
        text = explanation_scorer._template_explanation([])
        self.assertIn("SHAP attribution", text)

    def test_template_includes_top_evidence_items(self):
        text = explanation_scorer._template_explanation(evidence_list())
        self.assertIn("Times returned to product page", text)
        self.assertIn("4", text)
        self.assertIn("Product reviews read", text)

    def test_template_is_always_grounded_by_its_own_verification(self):
        """The fallback must pass the same check a regenerated rewrite would."""
        text = explanation_scorer._template_explanation(evidence_list())
        self.assertTrue(explanation_scorer._verify_grounded_text(text, evidence_list()))


if __name__ == "__main__":
    unittest.main()
