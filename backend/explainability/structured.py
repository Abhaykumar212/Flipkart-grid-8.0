from __future__ import annotations

from backend.domain.causes import RootCause
from backend.domain.enums import Decision, PolicyStatus
from backend.domain.interventions import InterventionId
from backend.policy_engine.engine import POLICY_VERSION, PolicyResult
from backend.policy_engine.reasons import PolicyReason
from backend.recommendation.ranker import RANKER_VERSION, ScoredIntervention
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.contracts import CausePrediction, CauseResult

from .templates import (
    CAUSE_STATEMENTS,
    INTERVENTION_COPY,
    action_statement,
    feature_statement,
    rejection_statement,
)
from .render import template_prose


def _dominant(causes: CauseResult) -> CausePrediction:
    return max(
        causes.root_causes,
        key=lambda item: item.probability,
        default=CausePrediction(RootCause.UNKNOWN, 0.0, ()),
    )


def intervention_payload(selected: ScoredIntervention | None) -> dict[str, object] | None:
    if selected is None or selected.candidate.intervention_id == InterventionId.NO_ACTION:
        return None
    headline, body, cta_label = INTERVENTION_COPY[selected.candidate.intervention_id]
    return {
        "type": selected.candidate.intervention_id.value,
        "display_name": selected.candidate.display_name,
        "channel": selected.channel.value if selected.channel else None,
        "headline": headline,
        "body": body,
        "cta_label": cta_label,
        "reason": action_statement(selected.candidate.intervention_id),
        "confidence": selected.confidence,
    }


def build_explanation(
    *,
    decision_id: str,
    features: dict[str, float],
    risk: RiskPrediction,
    causes: CauseResult,
    policy_results: tuple[PolicyResult, ...],
    ranked: tuple[ScoredIntervention, ...],
    selected: ScoredIntervention | None,
    decision: Decision,
) -> dict[str, object]:
    dominant = _dominant(causes)
    factor_names = [factor.feature for factor in risk.top_factors]
    observation_names = [
        name for name in factor_names if name in dominant.evidence_keys
    ]
    observation_names.extend(
        name for name in factor_names if name not in observation_names
    )
    observation_names = observation_names[:5]
    factors = {factor.feature: factor.shap for factor in risk.top_factors}
    observations = [
        {
            "feature": name,
            "value": features[name],
            "shap": factors.get(name, 0.0),
            "statement": feature_statement(name, features[name]),
        }
        for name in observation_names
    ]
    rejected = [
        {
            "intervention": result.candidate.intervention_id.value,
            "status": result.status.value,
            "reasons": [reason.value for reason in result.reasons],
            "replacement": (
                result.replacement.intervention_id.value if result.replacement else None
            ),
            "statement": rejection_statement(
                result.candidate.intervention_id.value,
                [reason.value for reason in result.reasons],
            ),
        }
        for result in policy_results
        if result.status != PolicyStatus.PASS
    ]
    if (
        all(item["intervention"] != InterventionId.LIMITED_TIME_DISCOUNT.value for item in rejected)
        and (selected is None or selected.candidate.intervention_id != InterventionId.LIMITED_TIME_DISCOUNT)
    ):
        rejected.append({
            "intervention": InterventionId.LIMITED_TIME_DISCOUNT.value,
            "status": PolicyStatus.REJECT.value,
            "reasons": [PolicyReason.PRICE_SENSITIVITY_NOT_VERIFIED.value],
            "replacement": None,
            "statement": rejection_statement(
                InterventionId.LIMITED_TIME_DISCOUNT.value,
                [PolicyReason.PRICE_SENSITIVITY_NOT_VERIFIED.value],
            ),
        })
    cause_probabilities = sorted(
        (item.probability for item in causes.root_causes), reverse=True
    )
    cause_margin = (
        cause_probabilities[0] - cause_probabilities[1]
        if len(cause_probabilities) > 1
        else cause_probabilities[0] if cause_probabilities else 0.0
    )
    selected_id = (
        selected.candidate.intervention_id if selected else InterventionId.NO_ACTION
    )
    action_confidence = selected.confidence if selected else 0.0
    explanation = {
        "decision_id": decision_id,
        "observations": observations,
        "risk": {
            "probability": risk.probability,
            "band": risk.band.value,
            "model_version": risk.model_version,
            "statement": (
                f"Abandonment risk is {risk.band.value.lower()} at "
                f"{round(risk.probability * 100)}%."
            ),
        },
        "inference": {
            "root_cause": dominant.cause.value,
            "probability": dominant.probability,
            "evidence_keys": list(dominant.evidence_keys),
            "statement": CAUSE_STATEMENTS[dominant.cause],
        },
        "action": {
            "decision": decision.value,
            "intervention": selected_id.value,
            "channel": selected.channel.value if selected and selected.channel else None,
            "confidence": action_confidence,
            "statement": action_statement(selected_id),
        },
        "rejected": rejected,
        "uncertainty": {
            "cause_margin": round(cause_margin, 6),
            "statement": (
                "Signals were conflicting; no confident diagnosis was made."
                if causes.abstained
                else "The selected cause had the strongest supported evidence."
            ),
        },
        "runner_up": ranked[1].to_dict() if len(ranked) > 1 else None,
        "versions": {
            "risk": risk.model_version,
            "root_cause": causes.model_version,
            "ranker": RANKER_VERSION,
            "policy": POLICY_VERSION,
        },
        "rendered_by": "template",
    }
    explanation["rendered_text"] = template_prose(explanation)
    return explanation
