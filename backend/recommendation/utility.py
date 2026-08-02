from __future__ import annotations

from dataclasses import dataclass

from backend import config
from backend.domain.causes import RootCause
from backend.domain.enums import CostLevel
from backend.domain.interventions import InterventionDefinition, InterventionId
from backend.root_cause.contracts import CausePrediction, CauseResult


DIRECT_COST = {
    CostLevel.ZERO: 0.0,
    CostLevel.LOW: 0.15,
    CostLevel.MEDIUM: 0.5,
    CostLevel.HIGH: 1.0,
}


@dataclass(frozen=True, slots=True)
class UtilityScore:
    score: float
    breakdown: dict[str, float]
    relevant_cause: CausePrediction | None


def _relevant_cause(
    candidate: InterventionDefinition,
    causes: CauseResult,
) -> CausePrediction | None:
    supported = {
        cause for cause in candidate.supported_causes if isinstance(cause, RootCause)
    }
    matches = [item for item in causes.root_causes if item.cause in supported]
    return max(matches, key=lambda item: item.probability, default=None)


def score_candidate(
    candidate: InterventionDefinition,
    features: dict[str, float],
    risk_probability: float,
    causes: CauseResult,
) -> UtilityScore:
    """Apply the exact §12.4 normalized utility formula."""

    if candidate.intervention_id == InterventionId.NO_ACTION:
        return UtilityScore(0.0, {
            "relevance": 0.0,
            "expected_uplift": 0.0,
            "user_affinity": 0.0,
            "information_gain": 0.0,
            "direct_cost_penalty": 0.0,
            "margin_risk_penalty": 0.0,
            "fatigue_penalty": 0.0,
            "intrusiveness_penalty": 0.0,
        }, None)

    relevant = _relevant_cause(candidate, causes)
    relevance = relevant.probability if relevant else 0.0
    expected_uplift = candidate.prior_uplift * risk_probability
    user_affinity = (
        features["u_affinity_incentive"]
        if candidate.cost_level == CostLevel.HIGH
        else features["u_affinity_informational"]
    )
    information_gain = 1 - causes.confidence
    direct_cost = DIRECT_COST[candidate.cost_level]
    margin_risk = 0.0
    if (
        candidate.intervention_id == InterventionId.LIMITED_TIME_DISCOUNT
        and features["c_value"] > 0
    ):
        discount_fraction = min(
            config.DEFAULT_DISCOUNT_PCT,
            candidate.max_discount_pct or config.DEFAULT_DISCOUNT_PCT,
        ) / 100
        margin_risk = min(
            1.0,
            discount_fraction * features["c_value"]
            / (features["c_value"] * 0.18),
        )
    fatigue = min(
        1.0,
        0.25 * features["i_shown_count"]
        + 0.40 * features["i_dismissal_count"],
    )
    intrusiveness = candidate.intrusiveness / 3
    breakdown = {
        "relevance": 0.40 * relevance,
        "expected_uplift": 0.30 * expected_uplift,
        "user_affinity": 0.20 * user_affinity,
        "information_gain": 0.10 * information_gain,
        "direct_cost_penalty": -0.15 * direct_cost,
        "margin_risk_penalty": -0.25 * margin_risk,
        "fatigue_penalty": -0.20 * fatigue,
        "intrusiveness_penalty": -0.10 * intrusiveness,
    }
    rounded = {name: round(value, 6) for name, value in breakdown.items()}
    return UtilityScore(round(sum(rounded.values()), 6), rounded, relevant)
