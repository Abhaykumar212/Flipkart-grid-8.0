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


# --- Phase 3: shopper profile + intervention plan --------------------------


class ShopperProfile(BaseModel):
    """Real (if lightweight) shopper history, replacing scalar placeholders.

    Backed by browser localStorage on the frontend, not an account service —
    still no auth exists — but these are genuine per-browser event lists
    instead of a single averaged counter.
    """

    model_config = ConfigDict(extra="forbid")

    wishlist_product_ids: List[str] = Field(default_factory=list)
    recent_view_product_ids: List[str] = Field(default_factory=list)
    past_purchase_product_ids: List[str] = Field(default_factory=list)


class ExplanationFactor(BaseModel):
    factor: str
    observation: str
    contribution: float


class RecommendedIntervention(BaseModel):
    lever_id: Literal[tuple(LEVER_IDS)]  # type: ignore[valid-type]
    headline: str
    rationale: str
    score: float
    confidence: Literal["high", "medium", "low"]
    expected_conversion_gain: float
    business_cost: Literal["low", "medium", "high"]
    llm_endorsed: bool
    explanation: List[ExplanationFactor] = Field(default_factory=list)


class InterventionPlan(BaseModel):
    """The Phase 3 handoff: what to actually show the shopper."""

    top_interventions: List[RecommendedIntervention] = Field(default_factory=list)
    fallback_intervention: Optional[RecommendedIntervention] = None
    excluded_lever_ids: List[str] = Field(default_factory=list)


# --- Companion chat: product-grounded Q&A -----------------------------------


class ProductReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: float = Field(ge=0, le=5)
    title: str = ""
    text: str = ""


class ProductSpecItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: str


class RatingDistributionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stars: int = Field(ge=1, le=5)
    count: int = Field(ge=0)


class ProductContext(BaseModel):
    """Everything the companion needs to answer product questions, sent by the
    client on each turn since the backend has no access to the frontend's mock
    catalog. Context-stuffed rather than retrieved — the per-product corpus
    (a handful of reviews, a short spec sheet) is small enough that handing the
    LLM all of it directly is simpler and more accurate than a retrieval step
    would be, with no embeddings or vector store needed.
    """

    model_config = ConfigDict(extra="forbid")

    title: str
    brand: str = ""
    category: str = ""
    mrp: float = Field(ge=0, default=0)
    selling_price: float = Field(ge=0, default=0)
    description: str = ""
    highlights: List[str] = Field(default_factory=list)
    specifications: List[ProductSpecItem] = Field(default_factory=list)
    delivery_free: bool = True
    estimated_delivery_days: int = Field(ge=0, le=60, default=3)
    emi_monthly: Optional[float] = None
    emi_months: Optional[int] = None
    offers: List[str] = Field(default_factory=list)
    seller_name: str = ""
    seller_rating: float = Field(ge=0, le=5, default=0)
    rating_value: float = Field(ge=0, le=5, default=0)
    rating_count: int = Field(ge=0, default=0)
    rating_distribution: List[RatingDistributionEntry] = Field(default_factory=list)
    in_stock: bool = True
    quantity_left: int = Field(ge=0, default=0)
    reviews: List[ProductReview] = Field(default_factory=list)


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class CompanionChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = "anonymous"
    product_context: Optional[ProductContext] = None
    # Populated only when the shopper has visited several similar products this
    # session and the companion is running an actual side-by-side comparison —
    # see pageContext.ts's findComparisonCandidates on the frontend for the
    # active-memory detection that triggers this.
    comparison_products: List[ProductContext] = Field(default_factory=list, max_length=4)
    # Real search queries this session (most-recent first), not a count — the
    # companion's active memory of what the shopper has actually been looking for.
    search_history: List[str] = Field(default_factory=list, max_length=15)
    messages: List[ChatMessage] = Field(min_length=1, max_length=20)


class CompanionChatResponse(BaseModel):
    status: Literal["success", "rate_limited", "not_configured", "error"]
    reply: Optional[str] = None
    model_used: Optional[str] = None
    latency_ms: float = 0.0
    message: Optional[str] = None


# --- Delivery decisions + session ledger ------------------------------------
#
# The delivery layer (`src/context/InterventionContext.tsx`) decides whether the
# ranked plan is worth the shopper's attention, at what intensity, on which
# surface. That decision used to live only in sessionStorage; these models are
# its write path and read-back, so the ledger survives a reload or a fresh tab.


class SuppressedLever(BaseModel):
    """A rung-3 lever the ranking offered and policy withheld."""

    model_config = ConfigDict(extra="forbid")

    lever_id: str
    reason: str


class DeliveryDecisionRequest(BaseModel):
    """One per pipeline run — mirrors `selectSurface`'s deliver/hold/elicit union."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    outcome: Literal["delivered", "held", "elicited"]
    reason: Optional[str] = None
    detail: Optional[str] = None
    root_cause: Optional[str] = None
    probability: Optional[float] = None
    # Present only when `outcome == "delivered"`.
    lever_id: Optional[str] = None
    intensity_rung: Optional[int] = None
    surface: Optional[str] = None
    confidence: Optional[str] = None
    suppressed: List[SuppressedLever] = Field(default_factory=list)


class HeldDecisionRecord(BaseModel):
    reason: Optional[str] = None
    rootCause: Optional[str] = None
    detail: Optional[str] = None
    at: float


class SuppressedLeverRecord(BaseModel):
    leverId: str
    reason: str
    at: float


class SpendAvoidedEntry(BaseModel):
    count: int
    assumedUnitValueInr: int
    totalInr: int


class LedgerOutcomes(BaseModel):
    accepted: int = 0
    dismissed: int = 0
    ignored: int = 0


class SessionLedgerResponse(BaseModel):
    """Field names are camelCase to match the panel's existing snapshot shape
    (`LedgerSnapshot` in `src/lib/interventionLedger.ts`), so the client can
    hydrate from this without a translation layer."""

    session_id: str
    shownByRung: List[int] = Field(default_factory=lambda: [0, 0, 0, 0])
    # do_nothing / (do_nothing + intervene) across this session's runs.
    silenceRate: float = 0.0
    outcomes: LedgerOutcomes = Field(default_factory=LedgerOutcomes)
    held: List[HeldDecisionRecord] = Field(default_factory=list)
    heldByReason: Dict[str, int] = Field(default_factory=dict)
    suppressedRung3: List[SuppressedLeverRecord] = Field(default_factory=list)
    spendAvoidedInr: int = 0
    spendAvoidedByLever: Dict[str, SpendAvoidedEntry] = Field(default_factory=dict)
    elicitation_count: int = 0
    inferred_count: int = 0


class ElicitationResponseRequest(BaseModel):
    """Payload for user-selected elicitation chip."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    chip: Literal["Price", "Trust or quality", "Still comparing"]
    probability: Optional[float] = None
    cart_context: CartContext = Field(default_factory=CartContext)
    shopper_profile: ShopperProfile = Field(default_factory=ShopperProfile)



# --- Inventory holds --------------------------------------------------------


class CartAddRequest(BaseModel):
    """A shopper committed to a product — releases any hold this session had."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    product_id: str


class ProductAvailability(BaseModel):
    """`quantity_left` is supplied by the caller, not stored server-side.

    The catalog lives in `src/data/products.ts`; a second copy on this side
    would be one more thing to keep in step for no gain. The backend owns the
    holds and nothing else, so it answers what it actually knows: how many of
    the caller's units are currently spoken for.
    """

    product_id: str
    quantity_left: int
    reserved: int
    available: int


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
        "critic_blocked",
        "rate_limited",
        "not_configured",
        "error",
    ]
    prediction: Dict[str, Any]
    gate: GateDecision
    analysis: Optional[RootCauseAnalysis] = None
    intervention_plan: Optional[InterventionPlan] = None
    model_used: Optional[str] = None
    latency_ms: float = 0.0
    message: Optional[str] = None
    trace: List[TraceSpan] = Field(default_factory=list)
