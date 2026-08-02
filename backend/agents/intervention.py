"""Phase 3 — Intelligent Intervention & Recommendation Engine.

Consumes the Phase 2 root-cause diagnosis (`RootCauseAnalysis`) plus session and
shopper context, and produces a ranked, explainable, executable set of
interventions. Deliberately makes **no second LLM call** — Phase 2 already spent
the LLM budget diagnosing *why*; this module answers *what to do about it* with a
deterministic scoring function over numbers Phase 1/2 already computed
(engineered features, SHAP impacts, the LLM's own lever proposals and
confidence).

Design mirrors `agents/gate.py` and `agents/root_cause.py`: plain functions over
typed inputs, no I/O beyond the in-memory `InterventionMemoryStore`, fully
unit-testable without network access.

Agents in this module, in the order they run:
    build_context        -- Context Agent
    build_candidates      -- Candidate Agent (unions the LLM's picks with the
                              full catalog filtered by diagnosed category)
    score_candidate        -- Ranking Agent's scoring function
    build_explanation      -- Explainability Agent
    build_intervention_plan -- orchestrator, calls the above in order

Every weight the Ranking Agent uses lives in one place, `SCORING_WEIGHTS`. A
future reinforcement-learning policy replaces the body of `score_candidate`
alone; the signature (candidate + context -> float) and everything downstream
of it stay unchanged. `InterventionMemoryStore`'s per-session log of
shown/accepted/dismissed/converted events is the (state, action, reward) trail
that policy would train on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..schemas import (
    ExplanationFactor,
    InterventionPlan,
    RecommendedIntervention,
    RootCauseAnalysis,
    ShopperProfile,
)
from .levers import LEVER_CATALOG
from .memory import InterventionMemoryStore

# Shopper-facing copy per lever. Kept separate from `levers.py`'s catalog,
# which is ranking/business data, not presentation text.
LEVER_HEADLINES: Dict[str, str] = {
    "free_delivery_waiver": "Free delivery, on us — checkout now",
    "targeted_discount_code": "Here's a discount code just for this cart",
    "emi_plan_highlight": "Split this into easy No-Cost EMIs",
    "price_drop_alert": "We'll alert you the moment the price drops",
    "delivery_speed_upgrade": "Get it faster — upgrade your delivery slot",
    "trust_badge_reassurance": "100% secure payments & easy returns",
    "guest_to_account_nudge": "Create an account in one tap to track this order",
    "saved_payment_prompt": "Save a payment method for faster checkout",
    "review_summary_surface": "See what other buyers really think",
    "stock_scarcity_nudge": "Almost out of stock — grab it before it's gone",
    "exit_intent_reminder": "Still deciding? Your cart is saved for you",
    "abandoned_cart_email": "We'll remind you about this cart later",
    "checkout_assist_chat": "Need a hand? Chat with us now",
    "payment_retry_help": "Payment didn't go through — try another method",
}

CONFIDENCE_NUMERIC: Dict[str, float] = {"high": 1.0, "medium": 0.6, "low": 0.3}
ENDORSEMENT_BY_RANK: List[float] = [1.0, 0.6, 0.3]

# Named-constant weights. This dict is the only thing a future RL policy would
# replace — `score_candidate`'s signature and every caller stay unchanged.
SCORING_WEIGHTS: Dict[str, float] = {
    "category_match": 3.0,
    "llm_endorsement": 2.0,
    "expected_conversion_gain": 2.5,
    "urgency": 1.5,
    "confidence": 1.0,
    "cost_penalty": 0.6,
    "repetition_penalty": 1.2,
}

TOP_N = 3


@dataclass
class InterventionContext:
    """Everything the Ranking Agent needs, assembled once per request."""

    probability: float
    confidence_numeric: float
    category_weight: Dict[str, float]
    llm_endorsement: Dict[str, float]
    llm_rationale: Dict[str, str]
    levers_to_avoid: Dict[str, str]
    shopper_profile: ShopperProfile
    memory: Optional[InterventionMemoryStore]
    session_id: str


@dataclass
class ScoredCandidate:
    lever_id: str
    score: float
    breakdown: Dict[str, float]
    category_match: float


def build_context(
    analysis: RootCauseAnalysis,
    probability: float,
    shopper_profile: ShopperProfile,
    session_id: str,
    memory: Optional[InterventionMemoryStore] = None,
) -> InterventionContext:
    """Context Agent — normalizes the diagnosis into scoring-ready lookups."""
    category_weight: Dict[str, float] = {analysis.primary_root_cause.category: 1.0}
    for factor in analysis.contributing_factors:
        category_weight.setdefault(factor.category, 0.5)

    ranked = sorted(analysis.recommended_levers, key=lambda lever: lever.priority)
    llm_endorsement: Dict[str, float] = {}
    llm_rationale: Dict[str, str] = {}
    for index, lever in enumerate(ranked):
        weight = ENDORSEMENT_BY_RANK[index] if index < len(ENDORSEMENT_BY_RANK) else 0.15
        llm_endorsement[lever.lever_id] = weight
        llm_rationale[lever.lever_id] = lever.rationale

    levers_to_avoid = {item.lever_id: item.reason for item in analysis.levers_to_avoid}

    return InterventionContext(
        probability=probability,
        confidence_numeric=CONFIDENCE_NUMERIC.get(analysis.confidence, 0.5),
        category_weight=category_weight,
        llm_endorsement=llm_endorsement,
        llm_rationale=llm_rationale,
        levers_to_avoid=levers_to_avoid,
        shopper_profile=shopper_profile,
        memory=memory,
        session_id=session_id,
    )


def build_candidates(context: InterventionContext) -> List[str]:
    """Candidate Agent — union of category-matched catalog levers and every
    lever the LLM endorsed, minus anything hard-excluded.

    Deliberately not capped at the LLM's 3 picks: the LLM only ever proposes up
    to 3, but the catalog may hold other levers that fit the same diagnosed
    category just as well, and the Ranking Agent — not the LLM — should decide
    which 3 actually surface.
    """
    candidates: List[str] = []
    for lever_id, meta in LEVER_CATALOG.items():
        if lever_id in context.levers_to_avoid:
            continue
        addresses = meta["addresses"]  # type: ignore[index]
        matches_category = any(category in context.category_weight for category in addresses)
        if matches_category or lever_id in context.llm_endorsement:
            candidates.append(lever_id)
    return candidates


def score_candidate(lever_id: str, context: InterventionContext) -> ScoredCandidate:
    """Ranking Agent — deterministic weighted score, no if-else cascade."""
    meta = LEVER_CATALOG[lever_id]
    addresses: List[str] = meta["addresses"]  # type: ignore[assignment]

    category_match = max((context.category_weight.get(c, 0.0) for c in addresses), default=0.0)
    llm_endorsement = context.llm_endorsement.get(lever_id, 0.0)
    expected_gain = float(meta["expected_conversion_gain"])
    cost_score = float(meta["cost_score"])
    urgency = category_match * context.probability

    repetition_penalty = 0.0
    if context.memory is not None:
        session = context.memory.get(context.session_id)
        if session.was_dismissed(lever_id):
            repetition_penalty = 1.0
        else:
            # Escalates with repeat exposure instead of a flat one-time dip, so a
            # suggestion the shopper hasn't acted on gradually loses its lead to
            # the next-best option rather than winning forever on a static diagnosis.
            shown = session.shown_count(lever_id)
            if shown > 0:
                repetition_penalty = min(0.9, 0.3 * shown)

    w = SCORING_WEIGHTS
    breakdown = {
        "category_match": w["category_match"] * category_match,
        "llm_endorsement": w["llm_endorsement"] * llm_endorsement,
        "expected_conversion_gain": w["expected_conversion_gain"] * expected_gain,
        "urgency": w["urgency"] * urgency,
        "confidence": w["confidence"] * context.confidence_numeric,
        "cost_penalty": -w["cost_penalty"] * (cost_score / 3.0),
        "repetition_penalty": -w["repetition_penalty"] * repetition_penalty,
    }
    score = sum(breakdown.values())
    return ScoredCandidate(lever_id=lever_id, score=score, breakdown=breakdown, category_match=category_match)


def build_explanation(
    candidate: ScoredCandidate,
    analysis: RootCauseAnalysis,
    context: InterventionContext,
) -> List[ExplanationFactor]:
    """Explainability Agent — reasoning trail built from the score breakdown
    and the SHAP evidence Phase 2 already produced. No free text is invented;
    every observation cites a number the pipeline already computed.
    """
    trail: List[ExplanationFactor] = []

    if candidate.category_match >= 1.0:
        trail.append(
            ExplanationFactor(
                factor="root_cause_match",
                observation=f"Diagnosed primary cause: {analysis.primary_root_cause.headline}",
                contribution=candidate.breakdown["category_match"],
            )
        )
    elif candidate.category_match > 0:
        trail.append(
            ExplanationFactor(
                factor="root_cause_match",
                observation="Matches a contributing (secondary) friction, not the primary cause",
                contribution=candidate.breakdown["category_match"],
            )
        )

    if candidate.lever_id in context.llm_endorsement:
        trail.append(
            ExplanationFactor(
                factor="agent_endorsement",
                observation=context.llm_rationale.get(candidate.lever_id, "Endorsed by the root-cause agent"),
                contribution=candidate.breakdown["llm_endorsement"],
            )
        )

    for evidence in analysis.primary_root_cause.supporting_evidence[:2]:
        trail.append(
            ExplanationFactor(
                factor=f"signal:{evidence.signal}",
                observation=f"{evidence.observed_value} — {evidence.why_it_matters}",
                contribution=evidence.shap_contribution,
            )
        )

    if candidate.breakdown["repetition_penalty"] < 0:
        trail.append(
            ExplanationFactor(
                factor="repetition_penalty",
                observation="Already shown or dismissed earlier this session",
                contribution=candidate.breakdown["repetition_penalty"],
            )
        )

    return trail


def _to_recommended(
    candidate: ScoredCandidate,
    analysis: RootCauseAnalysis,
    context: InterventionContext,
) -> RecommendedIntervention:
    meta = LEVER_CATALOG[candidate.lever_id]
    llm_endorsed = candidate.lever_id in context.llm_endorsement
    rationale = context.llm_rationale.get(
        candidate.lever_id,
        f"{meta['description']} Matches the diagnosed {analysis.primary_root_cause.category.replace('_', ' ')}.",
    )
    return RecommendedIntervention(
        lever_id=candidate.lever_id,
        headline=LEVER_HEADLINES[candidate.lever_id],
        rationale=rationale,
        score=round(candidate.score, 4),
        confidence=analysis.confidence,
        expected_conversion_gain=float(meta["expected_conversion_gain"]),
        business_cost=meta["business_cost"],  # type: ignore[arg-type]
        llm_endorsed=llm_endorsed,
        explanation=build_explanation(candidate, analysis, context),
    )


def build_intervention_plan(
    analysis: RootCauseAnalysis,
    probability: float,
    shopper_profile: ShopperProfile,
    session_id: str,
    memory: InterventionMemoryStore,
) -> InterventionPlan:
    """Orchestrator — Context -> Candidate -> Ranking -> Explainability."""
    context = build_context(analysis, probability, shopper_profile, session_id, memory)
    candidate_ids = build_candidates(context)

    scored = sorted(
        (score_candidate(lever_id, context) for lever_id in candidate_ids),
        key=lambda c: c.score,
        reverse=True,
    )

    top = scored[:TOP_N]
    top_ids = {c.lever_id for c in top}

    fallback_pool = [c for c in scored if c.lever_id not in top_ids]
    fallback_candidate = (
        min(fallback_pool, key=lambda c: LEVER_CATALOG[c.lever_id]["cost_score"])
        if fallback_pool
        else (top[-1] if top else None)
    )

    for candidate in top:
        memory.record(session_id, candidate.lever_id, "shown")

    return InterventionPlan(
        top_interventions=[_to_recommended(c, analysis, context) for c in top],
        fallback_intervention=(
            _to_recommended(fallback_candidate, analysis, context) if fallback_candidate else None
        ),
        excluded_lever_ids=list(context.levers_to_avoid),
    )
