from __future__ import annotations

from dataclasses import dataclass, replace
from functools import cmp_to_key

from backend.domain.enums import Channel, CostLevel
from backend.domain.interventions import InterventionDefinition, InterventionId
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.contracts import CauseResult

from .utility import score_candidate


RANKER_VERSION = "ranker-rules-v1"
COST_ORDER = {
    CostLevel.ZERO: 0,
    CostLevel.LOW: 1,
    CostLevel.MEDIUM: 2,
    CostLevel.HIGH: 3,
}


@dataclass(frozen=True, slots=True)
class ScoredIntervention:
    candidate: InterventionDefinition
    score: float
    confidence: float
    score_breakdown: dict[str, float]
    channel: Channel | None
    relevant_cause: str | None
    evidence_keys: tuple[str, ...]
    tie_break_applied: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "intervention": self.candidate.intervention_id.value,
            "score": self.score,
            "confidence": self.confidence,
            "score_breakdown": self.score_breakdown,
            "channel": self.channel.value if self.channel else None,
            "relevant_cause": self.relevant_cause,
            "evidence_keys": list(self.evidence_keys),
            "tie_break_applied": self.tie_break_applied,
        }


def _channel(candidate: InterventionDefinition, current_route: str | None) -> Channel | None:
    allowed = candidate.allowed_channels
    if current_route == "/checkout" and Channel.CHECKOUT_PANEL in allowed:
        return Channel.CHECKOUT_PANEL
    for preferred in (
        Channel.INLINE_CARD,
        Channel.BANNER,
        Channel.COMPARISON_DRAWER,
        Channel.ASSISTANT_PANEL,
        Channel.CHECKOUT_PANEL,
    ):
        if preferred in allowed:
            return preferred
    return None


def _compare(left: ScoredIntervention, right: ScoredIntervention) -> int:
    if abs(left.score - right.score) >= 0.05:
        return -1 if left.score > right.score else 1
    left_key = (
        COST_ORDER[left.candidate.cost_level],
        left.candidate.intrusiveness,
        left.candidate.intervention_id.value,
    )
    right_key = (
        COST_ORDER[right.candidate.cost_level],
        right.candidate.intrusiveness,
        right.candidate.intervention_id.value,
    )
    return (left_key > right_key) - (left_key < right_key)


def rules_score_all(
    candidates: tuple[InterventionDefinition, ...] | list[InterventionDefinition],
    features: dict[str, float],
    risk: RiskPrediction,
    causes: CauseResult,
    *,
    current_route: str | None = None,
) -> tuple[ScoredIntervention, ...]:
    """Score and deterministically order all approved candidates."""

    unique = {candidate.intervention_id: candidate for candidate in candidates}
    provisional = []
    for candidate in unique.values():
        utility = score_candidate(candidate, features, risk.probability, causes)
        relevant = utility.relevant_cause
        provisional.append(ScoredIntervention(
            candidate=candidate,
            score=utility.score,
            confidence=0.0,
            score_breakdown=utility.breakdown,
            channel=_channel(candidate, current_route),
            relevant_cause=relevant.cause.value if relevant else None,
            evidence_keys=relevant.evidence_keys if relevant else (),
        ))
    ordered = sorted(provisional, key=cmp_to_key(_compare))
    scored: list[ScoredIntervention] = []
    for index, item in enumerate(ordered):
        if item.candidate.intervention_id == InterventionId.NO_ACTION:
            confidence = 0.0
        else:
            runner_score = max(
                (other.score for other in ordered if other is not item),
                default=0.0,
            )
            separation = min(1.0, max(0.0, item.score - runner_score) / 0.25)
            cause_confidence = (
                next(
                    (cause.probability for cause in causes.root_causes if cause.cause.value == item.relevant_cause),
                    0.0,
                )
            )
            evidence_support = min(1.0, len(item.evidence_keys) / 3)
            confidence = (
                0.45 * cause_confidence
                + 0.30 * separation
                + 0.25 * evidence_support
            )
        tie_break = (
            index == 0
            and len(ordered) > 1
            and abs(item.score - ordered[1].score) < 0.05
        )
        scored.append(replace(
            item,
            confidence=round(confidence, 6),
            tie_break_applied=tie_break,
        ))
    return tuple(scored)


def score_all(
    candidates: tuple[InterventionDefinition, ...] | list[InterventionDefinition],
    features: dict[str, float],
    risk: RiskPrediction,
    causes: CauseResult,
    *,
    current_route: str | None = None,
) -> tuple[ScoredIntervention, ...]:
    """Select the configured ranker; rules remain the deterministic default."""

    from backend import config

    if config.RANKER_STRATEGY == "bandit":
        from .bandit import live_bandit

        return live_bandit.score_all(
            candidates,
            features,
            risk,
            causes,
            current_route=current_route,
        )
    return rules_score_all(
        candidates,
        features,
        risk,
        causes,
        current_route=current_route,
    )
