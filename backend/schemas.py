"""Shared request/response models for the pipeline API."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .agents.levers import LEVER_IDS, ROOT_CAUSE_CATEGORIES


# --- Cart context supplied by the storefront ------------------------------


class CartLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str
    title: str
    brand: str = ""
    category: str = ""
    quantity: int = Field(ge=1, le=50)
    selling_price: float = Field(ge=0)
    mrp: float = Field(ge=0)
    discount_percent: float = Field(ge=0, le=100, default=0)
    estimated_delivery_days: int = Field(ge=0, le=60, default=3)
    in_stock: bool = True
    price_dropped_recently: bool = False


class CartContext(BaseModel):
    """Human-meaningful cart state, used to make the analysis concrete."""

    model_config = ConfigDict(extra="forbid")

    lines: List[CartLine] = Field(default_factory=list)
    cart_total: float = Field(ge=0, default=0)
    mrp_total: float = Field(ge=0, default=0)
    delivery_fee: float = Field(ge=0, default=0)
    currency: str = "INR"
    cart_age_seconds: float = Field(ge=0, default=0)
    current_route: str = "/cart"


# --- Root cause analysis output -------------------------------------------


class Evidence(BaseModel):
    signal: str
    observed_value: str
    shap_contribution: float
    why_it_matters: str


class PrimaryRootCause(BaseModel):
    category: Literal[tuple(ROOT_CAUSE_CATEGORIES)]  # type: ignore[valid-type]
    headline: str
    explanation: str
    supporting_evidence: List[Evidence]


class ContributingFactor(BaseModel):
    category: Literal[tuple(ROOT_CAUSE_CATEGORIES)]  # type: ignore[valid-type]
    headline: str
    signal: str


class RecommendedLever(BaseModel):
    lever_id: Literal[tuple(LEVER_IDS)]  # type: ignore[valid-type]
    rationale: str
    expected_effect: str
    priority: int = Field(ge=1, le=10)


class LeverToAvoid(BaseModel):
    lever_id: Literal[tuple(LEVER_IDS)]  # type: ignore[valid-type]
    reason: str


class RootCauseAnalysis(BaseModel):
    """The contract Phase 3 consumes."""

    primary_root_cause: PrimaryRootCause
    contributing_factors: List[ContributingFactor] = Field(default_factory=list)
    shopper_narrative: str
    confidence: Literal["high", "medium", "low"]
    confidence_reasoning: str
    recommended_levers: List[RecommendedLever] = Field(default_factory=list)
    levers_to_avoid: List[LeverToAvoid] = Field(default_factory=list)


# --- Gate + envelope -------------------------------------------------------


class GateDecision(BaseModel):
    fired: bool
    threshold: float
    reason: str
    checks: Dict[str, Any] = Field(default_factory=dict)


class TraceSpan(BaseModel):
    id: str
    stage: str
    label: str
    status: str
    started_at: float
    duration_ms: float
    source: str
    detail: Dict[str, Any] = Field(default_factory=dict)


class RootCauseResponse(BaseModel):
    pipeline_run_id: str
    status: Literal[
        "success",
        "gate_not_met",
        "rate_limited",
        "not_configured",
        "error",
    ]
    prediction: Dict[str, Any]
    gate: GateDecision
    analysis: Optional[RootCauseAnalysis] = None
    model_used: Optional[str] = None
    latency_ms: float = 0.0
    message: Optional[str] = None
    trace: List[TraceSpan] = Field(default_factory=list)
