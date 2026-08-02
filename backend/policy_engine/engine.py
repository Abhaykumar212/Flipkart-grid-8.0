from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from backend import config
from backend.domain.enums import CostLevel, PolicyStatus
from backend.domain.interventions import InterventionDefinition, InterventionId
from backend.recommendation.ranker import ScoredIntervention
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.contracts import CauseResult
from backend.session_state.state import SessionState

from .reasons import PolicyReason
from .rules import ORDERED_RULES


POLICY_VERSION = "policy-v1"


@dataclass(frozen=True, slots=True)
class PolicyResult:
    candidate: InterventionDefinition
    status: PolicyStatus
    reasons: tuple[PolicyReason, ...] = ()
    stopped_at_rule: str | None = None
    replacement: InterventionDefinition | None = None

    @property
    def effective_candidate(self) -> InterventionDefinition | None:
        if self.status == PolicyStatus.REJECT:
            return None
        return self.replacement or self.candidate

    def to_dict(self) -> dict[str, object]:
        return {
            "intervention": self.candidate.intervention_id.value,
            "status": self.status.value,
            "reasons": [reason.value for reason in self.reasons],
            "stopped_at_rule": self.stopped_at_rule,
            "replacement": (
                self.replacement.intervention_id.value if self.replacement else None
            ),
        }


def evaluate_all(
    candidates: tuple[InterventionDefinition, ...] | list[InterventionDefinition],
    state: SessionState,
    features: dict[str, float],
    risk: RiskPrediction,
    causes: CauseResult,
    *,
    now: datetime | None = None,
) -> tuple[PolicyResult, ...]:
    evaluated_at = now or datetime.now(timezone.utc)
    results = []
    for candidate in candidates:
        result = PolicyResult(candidate, PolicyStatus.PASS)
        for rule_name, rule in ORDERED_RULES:
            verdict = rule(candidate, state, features, risk, causes, evaluated_at)
            if verdict.rejected:
                result = PolicyResult(
                    candidate,
                    PolicyStatus.REJECT,
                    (verdict.reason,),
                    rule_name,
                )
                break
        results.append(result)
    return tuple(results)


def approved_candidates(results: tuple[PolicyResult, ...]) -> tuple[InterventionDefinition, ...]:
    return tuple(
        candidate
        for result in results
        if (candidate := result.effective_candidate) is not None
    )


def finalize_discount_protection(
    results: tuple[PolicyResult, ...],
    ranked: tuple[ScoredIntervention, ...],
) -> tuple[PolicyResult, ...]:
    """Apply §12.5 checks that require utility scores and confidence."""

    by_id = {item.candidate.intervention_id: item for item in ranked}
    discount = by_id.get(InterventionId.LIMITED_TIME_DISCOUNT)
    if discount is None:
        return results
    low_cost = max(
        (
            item
            for item in ranked
            if item.candidate.intervention_id != InterventionId.LIMITED_TIME_DISCOUNT
            and item.candidate.cost_level in (CostLevel.ZERO, CostLevel.LOW)
        ),
        key=lambda item: item.score,
        default=None,
    )
    finalized = []
    for result in results:
        if (
            result.candidate.intervention_id != InterventionId.LIMITED_TIME_DISCOUNT
            or result.status == PolicyStatus.REJECT
        ):
            finalized.append(result)
            continue
        if low_cost is not None and low_cost.score >= discount.score - 0.10:
            finalized.append(replace(
                result,
                status=PolicyStatus.DOWNGRADE,
                reasons=(PolicyReason.LOW_COST_ALTERNATIVE_AVAILABLE,),
                stopped_at_rule="discount_protection",
                replacement=low_cost.candidate,
            ))
        elif discount.confidence < config.DISCOUNT_MIN_CONFIDENCE:
            finalized.append(replace(
                result,
                status=PolicyStatus.REJECT,
                reasons=(
                    PolicyReason.RECOMMENDATION_CONFIDENCE_BELOW_DISCOUNT_THRESHOLD,
                ),
                stopped_at_rule="discount_protection",
            ))
        else:
            finalized.append(result)
    return tuple(finalized)
