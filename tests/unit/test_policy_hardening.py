from dataclasses import replace
from datetime import datetime, timedelta, timezone

from backend.domain.enums import PolicyStatus, RiskBand
from backend.domain.interventions import InterventionId
from backend.feature_engine.schema import FEATURE_SCHEMA_V1
from backend.policy_engine.engine import PolicyResult, evaluate_all, finalize_discount_protection
from backend.policy_engine.reasons import PolicyReason
from backend.recommendation.catalogue import CATALOGUE_BY_ID
from backend.recommendation.ranker import ScoredIntervention
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.contracts import CauseResult
from backend.session_state.state import SessionState


def _scored(intervention: InterventionId, score: float) -> ScoredIntervention:
    candidate = CATALOGUE_BY_ID[intervention]
    channel = candidate.allowed_channels[0] if candidate.allowed_channels else None
    return ScoredIntervention(candidate, score, 0.8, {}, channel, None, ())


def test_discount_downgrade_preserves_original_and_replacement_entries() -> None:
    discount = CATALOGUE_BY_ID[InterventionId.LIMITED_TIME_DISCOUNT]
    results = (PolicyResult(discount, PolicyStatus.PASS),)
    finalized = finalize_discount_protection(results, (
        _scored(InterventionId.LIMITED_TIME_DISCOUNT, 0.50),
        _scored(InterventionId.PRICE_DROP_ALERT, 0.45),
    ))
    assert [(item.candidate.intervention_id, item.status) for item in finalized] == [
        (InterventionId.LIMITED_TIME_DISCOUNT, PolicyStatus.DOWNGRADE),
        (InterventionId.PRICE_DROP_ALERT, PolicyStatus.PASS),
    ]


def test_invalid_catalogue_entry_is_dropped_with_closed_reason() -> None:
    invalid = replace(CATALOGUE_BY_ID[InterventionId.REVIEW_SUMMARY], requires=("free_text",))
    features = {item.name: float(item.default) for item in FEATURE_SCHEMA_V1}
    features["review_summary_available"] = 1
    result = evaluate_all(
        (invalid,), SessionState(session_id="invalid"), features,
        RiskPrediction(0.8, 0.8, RiskBand.HIGH, "test", (), 0),
        CauseResult.unknown(),
    )[0]
    assert result.reasons == (PolicyReason.CATALOGUE_ENTRY_INVALID,)
    assert all(isinstance(reason, PolicyReason) for reason in result.reasons)


def test_catalogue_cooldown_expires_per_intervention() -> None:
    now = datetime(2026, 8, 2, tzinfo=timezone.utc)
    state = SessionState(session_id="cooldown")
    review = CATALOGUE_BY_ID[InterventionId.REVIEW_SUMMARY]
    state.cooldowns[review.intervention_id.value] = (now + timedelta(minutes=1)).isoformat()
    features = {item.name: float(item.default) for item in FEATURE_SCHEMA_V1}
    features["review_summary_available"] = 1
    risk = RiskPrediction(0.8, 0.8, RiskBand.HIGH, "test", (), 0)
    assert evaluate_all((review,), state, features, risk, CauseResult.unknown(), now=now)[0].reasons == (PolicyReason.COOLDOWN_ACTIVE,)
    assert evaluate_all((review,), state, features, risk, CauseResult.unknown(), now=now + timedelta(minutes=2))[0].status == PolicyStatus.PASS
