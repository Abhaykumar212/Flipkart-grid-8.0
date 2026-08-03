import random

import pytest

from backend import config
from backend.domain.causes import RootCause
from backend.domain.enums import RiskBand
from backend.domain.interventions import InterventionId
from backend.feature_engine.schema import FEATURE_SCHEMA_V1
from backend.policy_engine.engine import approved_candidates, evaluate_all
from backend.recommendation.bandit import ThompsonSamplingRanker, reward_value
from backend.recommendation.catalogue import CATALOGUE_BY_ID
from backend.recommendation.ranker import rules_score_all, score_all
from backend.risk_model.contracts import RiskPrediction
from backend.root_cause.contracts import CausePrediction, CauseResult
from backend.session_state.state import SessionState


def test_reward_is_strictly_additive():
    assert reward_value(
        conversion_value=2.0,
        intervention_cost=0.4,
        discount_cost=0.2,
        dismissed=True,
        repeated_intervention=True,
    ) == pytest.approx(0.9)


def test_bandit_converges_toward_higher_reward_arm():
    bandit = ThompsonSamplingRanker(seed=42)
    environment = random.Random(42)
    selected = []
    for _ in range(1_000):
        arm = bandit.choose(("LOW_REWARD", "HIGH_REWARD"), "DELIVERY_CONCERN")
        probability = 0.82 if arm == "HIGH_REWARD" else 0.18
        reward = float(environment.random() < probability)
        bandit.observe(arm, "DELIVERY_CONCERN", reward)
        selected.append(arm)
    assert selected[-200:].count("HIGH_REWARD") >= 175


def test_bandit_can_only_choose_supplied_policy_approved_candidates():
    bandit = ThompsonSamplingRanker(seed=7)
    approved = ("REVIEW_SUMMARY", "NO_ACTION")
    for _ in range(100):
        assert bandit.choose(approved, "PRODUCT_QUALITY_UNCERTAINTY") in approved
        assert bandit.choose(approved, "PRODUCT_QUALITY_UNCERTAINTY") != "LIMITED_TIME_DISCOUNT"


def test_bandit_scores_only_candidates_that_passed_policy():
    features = {item.name: float(item.default) for item in FEATURE_SCHEMA_V1}
    risk = RiskPrediction(0.2, 0.6, RiskBand.LOW, "test", (), 0)
    causes = CauseResult((
        CausePrediction(RootCause.PRICE_SENSITIVITY, 0.8, ("s_price_sort_count",)),
    ), "test", False, 0.8, 0)
    candidates = (
        CATALOGUE_BY_ID[InterventionId.LIMITED_TIME_DISCOUNT],
        CATALOGUE_BY_ID[InterventionId.NO_ACTION],
    )
    governed = approved_candidates(evaluate_all(
        candidates,
        SessionState(session_id="bandit-policy"),
        features,
        risk,
        causes,
    ))
    ranked = ThompsonSamplingRanker(seed=4).score_all(
        governed,
        features,
        risk,
        causes,
    )
    assert [item.candidate.intervention_id for item in ranked] == [InterventionId.NO_ACTION]


def test_rules_strategy_dispatch_is_byte_identical(monkeypatch):
    features = {item.name: float(item.default) for item in FEATURE_SCHEMA_V1}
    risk = RiskPrediction(0.8, 0.6, RiskBand.HIGH, "test", (), 0)
    causes = CauseResult((
        CausePrediction(RootCause.PRODUCT_QUALITY_UNCERTAINTY, 0.8, ("s_review_open_count",)),
    ), "test", False, 0.8, 0)
    candidates = (
        CATALOGUE_BY_ID[InterventionId.REVIEW_SUMMARY],
        CATALOGUE_BY_ID[InterventionId.NO_ACTION],
    )
    monkeypatch.setattr(config, "RANKER_STRATEGY", "rules")
    assert score_all(candidates, features, risk, causes) == rules_score_all(
        candidates, features, risk, causes
    )


def test_bandit_score_breakdown_remains_auditable():
    features = {item.name: float(item.default) for item in FEATURE_SCHEMA_V1}
    risk = RiskPrediction(0.8, 0.6, RiskBand.HIGH, "test", (), 0)
    causes = CauseResult((
        CausePrediction(RootCause.PRODUCT_QUALITY_UNCERTAINTY, 0.8, ("s_review_open_count",)),
    ), "test", False, 0.8, 0)
    ranked = ThompsonSamplingRanker(seed=8).score_all(
        (CATALOGUE_BY_ID[InterventionId.REVIEW_SUMMARY],),
        features,
        risk,
        causes,
    )
    assert sum(ranked[0].score_breakdown.values()) == pytest.approx(ranked[0].score, abs=1e-6)
