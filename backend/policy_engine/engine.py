from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from backend import config
from backend.domain.enums import PolicyStatus
from backend.domain.interventions import InterventionDefinition, InterventionId
from backend.recommendation.ranker import ScoredIntervention
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.contracts import CauseResult
from backend.session_state.state import SessionState
from backend.recommendation.catalogue import CATALOGUE_BY_ID

from .reasons import PolicyReason, REQUIREMENT_REASONS
from .rules import ORDERED_RULES


POLICY_VERSION = "policy-v1"


def _valid(candidate: InterventionDefinition) -> bool:
    return (
        isinstance(candidate.intervention_id, InterventionId)
        and 0 <= candidate.intrusiveness <= 3
        and candidate.cooldown_minutes >= 0
        and 0 <= candidate.prior_uplift <= 1
        and all(requirement in REQUIREMENT_REASONS for requirement in candidate.requires)
    )


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
        if not _valid(candidate):
            results.append(PolicyResult(candidate, PolicyStatus.REJECT, (PolicyReason.CATALOGUE_ENTRY_INVALID,), "catalogue_validation"))
            continue
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
    low_cost = by_id.get(InterventionId.PRICE_DROP_ALERT)
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
                replacement=CATALOGUE_BY_ID[InterventionId.PRICE_DROP_ALERT],
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
    if any(item.status == PolicyStatus.DOWNGRADE for item in finalized) and not any(
        item.candidate.intervention_id == InterventionId.PRICE_DROP_ALERT for item in finalized
    ):
        finalized.append(PolicyResult(CATALOGUE_BY_ID[InterventionId.PRICE_DROP_ALERT], PolicyStatus.PASS))
    return tuple(finalized)
