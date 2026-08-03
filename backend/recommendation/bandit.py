from __future__ import annotations

from dataclasses import dataclass, replace
import random
from threading import RLock
from typing import TYPE_CHECKING, Iterable

from backend.domain.causes import RootCause
from backend.domain.interventions import InterventionDefinition, InterventionId
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.contracts import CauseResult

if TYPE_CHECKING:
    from backend.recommendation.ranker import ScoredIntervention


@dataclass(slots=True)
class BetaPosterior:
    alpha: float = 1.0
    beta: float = 1.0


def reward_value(
    *,
    conversion_value: float,
    intervention_cost: float = 0.0,
    discount_cost: float = 0.0,
    dismissed: bool = False,
    repeated_intervention: bool = False,
) -> float:
    return (
        conversion_value
        - intervention_cost
        - discount_cost
        - 0.3 * float(dismissed)
        - 0.2 * float(repeated_intervention)
    )


class ThompsonSamplingRanker:
    """Contextual Beta bandit that only reorders policy-approved candidates."""

    def __init__(self, *, seed: int | None = None) -> None:
        self._posteriors: dict[tuple[str, str], BetaPosterior] = {}
        self._random = random.Random(seed)
        self._lock = RLock()

    @staticmethod
    def _cause(causes: CauseResult) -> str:
        dominant = max(
            causes.root_causes,
            key=lambda item: item.probability,
            default=None,
        )
        return dominant.cause.value if dominant else RootCause.UNKNOWN.value

    def posterior(self, intervention_id: str, cause: str) -> BetaPosterior:
        with self._lock:
            return self._posteriors.setdefault(
                (intervention_id, cause),
                BetaPosterior(),
            )

    def observe(self, intervention_id: str, cause: str, reward: float) -> None:
        """Update with a bounded fractional reward (negative rewards are failures)."""

        success = min(1.0, max(0.0, float(reward)))
        with self._lock:
            posterior = self._posteriors.setdefault(
                (intervention_id, cause),
                BetaPosterior(),
            )
            posterior.alpha += success
            posterior.beta += 1.0 - success

    def choose(self, intervention_ids: Iterable[str], cause: str) -> str:
        choices = tuple(intervention_ids)
        if not choices:
            raise ValueError("at least one intervention is required")
        with self._lock:
            samples = {
                intervention_id: self._random.betavariate(
                    self._posteriors.setdefault(
                        (intervention_id, cause), BetaPosterior()
                    ).alpha,
                    self._posteriors[(intervention_id, cause)].beta,
                )
                for intervention_id in choices
            }
        return max(choices, key=lambda item: (samples[item], item))

    def score_all(
        self,
        candidates: tuple[InterventionDefinition, ...] | list[InterventionDefinition],
        features: dict[str, float],
        risk: RiskPrediction,
        causes: CauseResult,
        *,
        current_route: str | None = None,
    ) -> tuple["ScoredIntervention", ...]:
        from backend.recommendation.ranker import COST_ORDER, rules_score_all

        baseline = rules_score_all(
            candidates,
            features,
            risk,
            causes,
            current_route=current_route,
        )
        cause = self._cause(causes)
        rescored = []
        with self._lock:
            for item in baseline:
                if item.candidate.intervention_id == InterventionId.NO_ACTION:
                    rescored.append(item)
                    continue
                key = (item.candidate.intervention_id.value, cause)
                posterior = self._posteriors.setdefault(key, BetaPosterior())
                sample = self._random.betavariate(posterior.alpha, posterior.beta)
                # Policy/rule utility remains a stabilizing term while the sampled
                # posterior supplies the exploration/exploitation ordering.
                score = 0.7 * sample + 0.3 * max(-0.7, item.score)
                breakdown = {
                    "rule_utility": round(0.3 * item.score, 6),
                    "bandit_sample": round(0.7 * sample, 6),
                }
                rescored.append(replace(
                    item,
                    score=round(score, 6),
                    score_breakdown=breakdown,
                ))
        return tuple(sorted(
            rescored,
            key=lambda item: (
                -item.score,
                COST_ORDER[item.candidate.cost_level],
                item.candidate.intrusiveness,
                item.candidate.intervention_id.value,
            ),
        ))


live_bandit = ThompsonSamplingRanker()
