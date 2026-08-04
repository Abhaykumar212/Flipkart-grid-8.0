"""Bridges the LLM reasoning agent into the live decision pipeline.

The risk model scores the session and produces SHAP over all 62 risk features.
That attribution, plus the readable feature vector and the cart, goes to the
LLM, which decides the root cause and which levers deserve to fire. The trained
multi-label cause model becomes the fallback for when the LLM cannot answer —
no key, rate limited, budget spent, or a malformed response.

The agent *proposes*; `policy_engine` still disposes. Nothing here can put an
intervention in front of a shopper that the policy rules would have rejected,
which is what keeps a confident-but-wrong model from spending margin.

Budget
------
Every decision would otherwise be an LLM call, and browsing triggers make
decisions frequent. Two things stop that draining a free-tier quota: a
per-session cap, and a signature cache — an unchanged material situation reuses
the previous diagnosis instead of paying for an identical one.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, replace
from typing import Any, Dict, Optional, Tuple

from .. import config
from ..observability.latency import metrics_registry
from ..domain.causes import RootCause
from ..domain.interventions import InterventionId
from ..feature_engine.schema import RISK_MODEL_FEATURES
from ..risk_model.contracts import RiskPrediction
from ..root_cause.contracts import CausePrediction, CauseResult
from ..schemas import RootCauseAnalysis
from ..session_state.state import SessionState
from . import root_cause

#: How confident the agent's own word is worth. `low` sits just under
#: MIN_RECOMMENDATION_CONFIDENCE so a hedged diagnosis tends toward ABSTAIN.
_CONFIDENCE_NUMERIC: Dict[str, float] = {"high": 0.90, "medium": 0.72, "low": 0.54}

#: Weight given to the agent's 1st, 2nd and 3rd choice. Anything it ranked lower
#: is still endorsed, but only faintly.
_ENDORSEMENT_BY_RANK: Tuple[float, ...] = (1.0, 0.6, 0.3)

MODEL_VERSION = "llm-rca-v1"

_KNOWN_FEATURES = frozenset(RISK_MODEL_FEATURES)
_MAX_CACHE_ENTRIES = 256

LOGGER = logging.getLogger("backend.reasoning")

#: Why the model answered instead of the agent. Surfaced to the UI so a demo
#: never silently looks like it is reasoning when it has fallen back.
FALLBACK_DISABLED = "model:disabled"
FALLBACK_NO_SHAP = "model:no_attribution"
FALLBACK_BUDGET = "model:session_budget_spent"
FALLBACK_RATE_LIMITED = "model:rate_limited"
FALLBACK_ERROR = "model:agent_error"


@dataclass(slots=True)
class Diagnosis:
    """What the agent concluded, in the pipeline's own vocabulary."""

    causes: CauseResult
    #: intervention id -> endorsement weight in [0, 1].
    endorsements: Dict[str, float]
    #: Levers the agent explicitly argued against.
    avoid: frozenset[str]
    narrative: str
    headline: str
    explanation: str
    confidence_label: str
    confidence_reasoning: str
    model_used: str
    latency_ms: float
    path: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline": self.headline,
            "explanation": self.explanation,
            "narrative": self.narrative,
            "confidence": self.confidence_label,
            "confidence_reasoning": self.confidence_reasoning,
            "endorsed": sorted(self.endorsements, key=self.endorsements.get, reverse=True),
            "avoided": sorted(self.avoid),
            "model": self.model_used,
            "latency_ms": self.latency_ms,
            "path": self.path,
        }


@dataclass(slots=True)
class _Entry:
    signature: str
    at: float
    diagnosis: Diagnosis
    runs: int = 0


_CACHE: Dict[str, _Entry] = {}


def reset(session_id: Optional[str] = None) -> None:
    """Clear cached diagnoses. Used by tests and the demo reset."""
    if session_id is None:
        _CACHE.clear()
    else:
        _CACHE.pop(session_id, None)


class _NullRecorder:
    """`analyse` wants a TraceRecorder; the pipeline has no trace to attach to."""

    def span(self, *_args: Any, **_kwargs: Any) -> Any:
        return _NullSpan()

    def add(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _NullSpan:
    def __enter__(self) -> Dict[str, Any]:
        return {}

    def __exit__(self, *_args: Any) -> bool:
        return False


def _describe_cart(state: SessionState) -> str:
    cart = state.cart or {}
    items = [item for item in cart.get("items", []) if isinstance(item, dict)]
    route = state.current_route or "/"
    if not items:
        product = state.current_product_id or "no product"
        return (
            f"Cart is empty — the shopper is still browsing ({product}), on {route}. "
            "Only informational help is appropriate."
        )
    rows = [
        "  - {quantity}x {title} (₹{price:,.0f})".format(
            quantity=item.get("quantity", 1),
            title=item.get("title") or item.get("product_id", "item"),
            price=float(item.get("unit_price", 0) or 0),
        )
        for item in items
    ]
    header = (
        f"Cart total ₹{float(cart.get('value', 0) or 0):,.0f} "
        f"(MRP ₹{float(cart.get('mrp_total', 0) or 0):,.0f}), "
        f"delivery fee ₹{float(cart.get('delivery_fee', 0) or 0):,.0f}, "
        f"{int(cart.get('item_count', 0) or 0)} items, shopper is on {route}."
    )
    return header + "\n" + "\n".join(rows)


def _to_cause_result(
    analysis: RootCauseAnalysis,
    latency_ms: float,
) -> CauseResult:
    """Translate the agent's answer into the contract the pipeline consumes."""
    confidence = _CONFIDENCE_NUMERIC.get(analysis.confidence, 0.6)
    primary = RootCause(analysis.primary_root_cause.category)
    evidence = tuple(
        item.signal
        for item in analysis.primary_root_cause.supporting_evidence
        if item.signal in _KNOWN_FEATURES
    )
    predictions = [CausePrediction(primary, confidence, evidence[:5])]
    seen = {primary}
    for factor in analysis.contributing_factors:
        cause = RootCause(factor.category)
        if cause in seen or cause == RootCause.UNKNOWN:
            continue
        seen.add(cause)
        keys = (factor.signal,) if factor.signal in _KNOWN_FEATURES else ()
        predictions.append(CausePrediction(cause, round(confidence * 0.6, 6), keys))
    abstained = primary == RootCause.UNKNOWN
    return CauseResult(
        root_causes=tuple(predictions),
        model_version=MODEL_VERSION,
        abstained=abstained,
        confidence=confidence,
        latency_ms=latency_ms,
    )


def _endorsements(analysis: RootCauseAnalysis) -> Dict[str, float]:
    ordered = sorted(analysis.recommended_levers, key=lambda lever: lever.priority)
    weights: Dict[str, float] = {}
    for rank, lever in enumerate(ordered):
        weight = _ENDORSEMENT_BY_RANK[rank] if rank < len(_ENDORSEMENT_BY_RANK) else 0.15
        weights.setdefault(lever.lever_id, weight)
    return weights


def endorsed_candidates(endorsements: Dict[str, float]) -> Tuple[InterventionId, ...]:
    """Agent picks as catalogue ids, so they can join the candidate set.

    The agent may endorse a lever whose `supported_causes` don't list the cause
    it diagnosed. That is a legitimate cross-cause judgement, so the pick is
    added to the candidate pool rather than dropped — the policy engine is what
    decides whether it is allowed to run.
    """
    ids = []
    for lever_id in endorsements:
        try:
            ids.append(InterventionId(lever_id))
        except ValueError:  # pragma: no cover - enum is schema-enforced upstream
            continue
    return tuple(ids)


def diagnose(
    session_id: str,
    state: SessionState,
    features: Dict[str, float],
    risk: RiskPrediction,
    *,
    force: bool = False,
    now: Optional[float] = None,
) -> Tuple[Optional[Diagnosis], str]:
    """Ask the agent why this session is at risk.

    Returns `(diagnosis, path)`. A `None` diagnosis means the caller should use
    the trained cause model; `path` says why, so the UI can be honest about it.
    """

    if not config.REASONING_LLM_ENABLED or not config.llm_is_configured():
        return None, FALLBACK_DISABLED
    if not risk.shap_by_feature:
        return None, FALLBACK_NO_SHAP

    moment = now if now is not None else time.time()
    signature = root_cause.build_feature_signature(features)
    entry = _CACHE.get(session_id)

    if (
        entry is not None
        and not force
        and entry.signature == signature
        and moment - entry.at < config.RCA_COOLDOWN_SECONDS
    ):
        metrics_registry.increment("reasoning_agent", label="cache")
        return replace(entry.diagnosis, path="cache"), "cache"

    runs = entry.runs if entry else 0
    if runs >= config.RCA_MAX_PER_SESSION:
        metrics_registry.increment("reasoning_agent", label="budget")
        return None, FALLBACK_BUDGET

    analysis, meta = root_cause.analyse(
        risk.probability,
        risk.band.value,
        risk.confidence,
        features,
        risk.shap_by_feature,
        _describe_cart(state),
        _NullRecorder(),
    )
    if analysis is None:
        rate_limited = bool(meta.get("rate_limited"))
        path = FALLBACK_RATE_LIMITED if rate_limited else FALLBACK_ERROR
        metrics_registry.increment(
            "reasoning_agent", label="rate_limited" if rate_limited else "error"
        )
        LOGGER.warning(
            "reasoning agent unavailable, using cause model: session=%s reason=%s error=%s",
            session_id,
            path,
            meta.get("error"),
        )
        return None, path

    diagnosis = Diagnosis(
        causes=_to_cause_result(analysis, float(meta.get("latency_ms", 0.0))),
        endorsements=_endorsements(analysis),
        avoid=frozenset(item.lever_id for item in analysis.levers_to_avoid),
        narrative=analysis.shopper_narrative,
        headline=analysis.primary_root_cause.headline,
        explanation=analysis.primary_root_cause.explanation,
        confidence_label=analysis.confidence,
        confidence_reasoning=analysis.confidence_reasoning,
        model_used=str(meta.get("model_used") or config.RCA_MODEL),
        latency_ms=float(meta.get("latency_ms", 0.0)),
        path="llm",
    )

    if len(_CACHE) >= _MAX_CACHE_ENTRIES and session_id not in _CACHE:
        _CACHE.pop(next(iter(_CACHE)), None)
    _CACHE[session_id] = _Entry(
        signature=signature,
        at=moment,
        diagnosis=diagnosis,
        runs=runs + 1,
    )
    metrics_registry.increment("reasoning_agent", label="llm")
    return diagnosis, "llm"
