"""The reasoning agent — diagnoses *why* a session is at risk.

Given the risk model's probability *and its SHAP attribution over the 67-feature
vector*, this agent produces structured JSON naming the root cause and the
intervention levers that fit it.

Design intent
-------------
The agent explains **the model's own attribution**. Its evidence array is built
from SHAP values, not from free association over a prompt, so it cannot name a
cause the model did not attribute. That property is what makes the output
defensible: the LLM isn't guessing, it's verbalising the model's reasoning.

Its vocabulary comes from `levers.py`, which derives from the executable
catalogue — so a hallucinated cause or lever is rejected by the strict
`json_schema` enum at the API boundary, and again by pydantic locally.

Why some features are withheld from the evidence array
------------------------------------------------------
`pay_method_on_file` and `pay_checkout_max_step` are among the risk model's
highest-gain features, and left in the evidence they swamp everything else —
every session gets diagnosed as a checkout problem, because how *far* someone
got through the funnel dominates the attribution. They describe how risky a
session is, not why the shopper is hesitating. They stay in the prompt as
context under SESSION FACTS, but never as rankable evidence.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple

from .. import config
from ..explainability.narratives import NARRATIVES, format_value, informative, statement
from ..feature_engine.schema import RISK_MODEL_FEATURES
from ..llm import GroqClient, RateLimitedError
from ..schemas import CartContext, RootCauseAnalysis
from .levers import (
    CATEGORY_DESCRIPTIONS,
    LEVER_IDS,
    ROOT_CAUSE_CATEGORIES,
    catalog_for_prompt,
)

# Funnel-progress and session-mechanics signals. Real inputs to the risk score,
# but they answer "how far" and "how fast", not "why" — see the module docstring.
_NON_DIAGNOSTIC: frozenset[str] = frozenset({
    "pay_method_on_file",
    "pay_checkout_max_step",
    "s_duration_seconds",
    "s_event_velocity_per_min",
    "x_hour_of_day",
})

#: The subset of the risk vector the agent may rank evidence over.
#: `RISK_MODEL_FEATURES` already excludes the `i_*` intervention-history group.
DIAGNOSTIC_FEATURES: Tuple[str, ...] = tuple(
    name for name in RISK_MODEL_FEATURES if name not in _NON_DIAGNOSTIC
)

# Features that materially change a diagnosis. Used for dedup hashing so an
# identical situation doesn't buy a second identical LLM call.
MATERIAL_FEATURES: Tuple[str, ...] = (
    "c_value",
    "c_item_count",
    "c_promo_applied",
    "c_max_price_drop_pct",
    "d_check_count",
    "d_max_days",
    "d_fee_pct_of_cart",
    "pay_failure_count",
    "pay_method_change_count",
    "s_review_open_count",
    "s_similar_product_view_count",
    "s_comparison_count",
    "s_coupon_search_count",
    "s_price_sort_count",
    "s_cart_add_count",
    "s_distinct_products_viewed",
    "p_any_low_stock",
    "p_any_out_of_stock",
)

#: Review dwell is continuous, so it can't go in the signature raw without
#: re-triggering on every tick. Bucketed, sustained reading still registers as a
#: genuinely new situation.
DWELL_BUCKET_SECONDS = 15.0

#: What the shopper actually *did*. These are reported to the agent verbatim,
#: independently of SHAP, because the risk model routinely attributes near-zero
#: to them — it doesn't need review-reading to score risk once idle time and
#: cart state are known. Near-zero SHAP is not evidence the behaviour is
#: irrelevant to *why*, which is the question the agent is answering.
BEHAVIOUR_SIGNALS: Tuple[str, ...] = (
    "s_review_open_count",
    "s_review_dwell_seconds",
    "s_similar_product_view_count",
    "s_comparison_count",
    "s_distinct_products_viewed",
    "s_product_view_count",
    "s_search_count",
    "s_price_sort_count",
    "s_coupon_search_count",
    "s_cart_view_count",
    "s_cart_add_count",
    "s_cart_remove_count",
    "s_cart_product_switch_count",
    "s_checkout_start_count",
    "s_back_from_checkout_count",
    "s_idle_seconds_current",
    "d_check_count",
    "pay_failure_count",
    "pay_method_change_count",
    "p_any_low_stock",
    "p_any_out_of_stock",
    "c_promo_applied",
    "c_max_price_drop_pct",
)

# Prompt grouping. Order is presentation only; membership decides what the agent
# sees as plain context versus ranked evidence.
_FACT_GROUPS: Dict[str, Tuple[str, ...]] = {
    "Cart": (
        "c_value",
        "c_item_count",
        "c_distinct_categories",
        "c_value_to_aov_ratio",
        "c_age_seconds",
        "c_promo_applied",
        "c_discount_pct_available",
        "c_max_price_drop_pct",
    ),
    "Browsing and research": (
        "s_product_view_count",
        "s_distinct_products_viewed",
        "s_review_open_count",
        "s_review_dwell_seconds",
        "s_similar_product_view_count",
        "s_comparison_count",
        "s_search_count",
        "s_idle_seconds_current",
    ),
    "Price behaviour": (
        "s_price_sort_count",
        "s_coupon_search_count",
        "u_discount_usage_rate",
    ),
    "Delivery": ("d_max_days", "d_min_days", "d_fee", "d_fee_pct_of_cart", "d_check_count"),
    "Product": ("p_max_item_price", "p_avg_rating", "p_min_rating_count", "p_any_low_stock", "p_any_out_of_stock"),
    "Checkout and payment (context only — not evidence for a cause)": (
        "pay_method_on_file",
        "pay_checkout_max_step",
        "pay_failure_count",
        "pay_method_change_count",
        "pay_emi_eligible",
        "s_checkout_start_count",
        "s_back_from_checkout_count",
    ),
    "Shopper history": (
        "u_lifetime_orders",
        "u_prior_abandonment_rate",
        "u_avg_order_value",
        "u_days_since_last_purchase",
        "u_return_rate",
        "u_is_new_user",
    ),
    "Session context": ("x_is_mobile", "x_is_late_night", "x_is_weekend", "x_is_returning_user"),
}


def _value_text(name: str, value: float) -> str:
    """Render one reading the way the rest of the product renders it."""
    narrative = NARRATIVES.get(name)
    if narrative is None:
        return f"{value:.3f}" if not float(value).is_integer() else str(int(value))
    return format_value(float(value), narrative.kind)


def build_feature_signature(features: Dict[str, float]) -> str:
    """Stable hash of the diagnosis-relevant features, for dedup."""
    parts = [f"{name}={round(float(features.get(name, 0)), 3)}" for name in MATERIAL_FEATURES]
    dwell = float(features.get("s_review_dwell_seconds", 0.0))
    parts.append(f"dwell_bucket={int(dwell // DWELL_BUCKET_SECONDS)}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def build_evidence(
    features: Dict[str, float],
    feature_impacts: Dict[str, float],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Top signed SHAP contributors within the diagnostic subset.

    Positive SHAP pushes toward abandonment, negative pulls toward conversion.
    Both directions are included: knowing what is *holding the shopper in* is as
    useful for choosing a lever as knowing what is pushing them away.
    """
    scoped = {
        name: impact
        for name, impact in feature_impacts.items()
        if name in DIAGNOSTIC_FEATURES
    }
    # The legacy 22-feature service speaks a different vocabulary. Rank whatever
    # it hands us rather than returning an empty evidence array.
    pool = scoped or feature_impacts
    ranked = sorted(pool.items(), key=lambda kv: abs(kv[1]), reverse=True)[:limit]
    evidence = []
    for name, impact in ranked:
        raw_value = features.get(name)
        evidence.append(
            {
                "signal": name,
                "observed_value": (
                    _value_text(name, float(raw_value)) if raw_value is not None else "derived"
                ),
                "statement": (
                    statement(name, float(raw_value))
                    if raw_value is not None and name in NARRATIVES
                    else name.replace("_", " ")
                ),
                "shap_contribution": round(float(impact), 4),
                "direction": (
                    "increases abandonment risk" if impact > 0 else "reduces abandonment risk"
                ),
            }
        )
    return evidence


def describe_cart(cart: CartContext) -> str:
    if not cart.lines:
        return "Cart contents were not supplied."
    rows = []
    for line in cart.lines:
        bits = [f"{line.quantity}x {line.title}", f"₹{line.selling_price:,.0f}"]
        if line.discount_percent > 0:
            bits.append(f"{line.discount_percent:.0f}% off ₹{line.mrp:,.0f}")
        bits.append(f"delivery in {line.estimated_delivery_days}d")
        if line.price_dropped_recently:
            bits.append("price recently dropped")
        if not line.in_stock:
            bits.append("OUT OF STOCK")
        rows.append("  - " + ", ".join(bits))
    header = (
        f"Cart total ₹{cart.cart_total:,.0f} (MRP ₹{cart.mrp_total:,.0f}), "
        f"delivery fee ₹{cart.delivery_fee:,.0f}, "
        f"cart is {cart.cart_age_seconds:.0f}s old, shopper is on {cart.current_route}."
    )
    return header + "\n" + "\n".join(rows)


_describe_cart = describe_cart  # retained for existing callers


SYSTEM_PROMPT = """You are a cart-abandonment root cause analyst for an Indian e-commerce platform.

A gradient-boosted model has already scored this session's abandonment risk and produced SHAP attributions showing exactly which signals drove that score. Your job is to explain WHY, grounded strictly in that attribution, and to choose what the platform should do about it.

Rules:
1. OBSERVED BEHAVIOUR decides WHICH cause. SHAP decides HOW STRONGLY the model already weights it. Pick the cause the behaviour supports; do not invent causes that neither block supports.
2. A signal with near-zero SHAP is NOT evidence that the behaviour is irrelevant. The risk model often scores risk from cart state and idle time alone, so review-reading or comparison activity can carry ~0.0 SHAP while still being the whole reason the shopper is hesitating. Never conclude "no concern" from a small SHAP value.
3. Positive SHAP pushes toward abandonment; negative pulls toward conversion. A large negative value is a REASSURING signal — never cite it as the reason a shopper is about to leave. In particular, near-zero idle time means the shopper is actively engaged, which is the opposite of low purchase intent.
4. The SHAP evidence deliberately excludes checkout-funnel-progress facts (steps completed, payment method on file) — they tell you HOW FAR a shopper got, not WHY. They appear under SESSION FACTS as context only; never cite them as support for a root cause.
5. Quote concrete observed values (amounts, counts, days) in your explanation — be specific, not generic.
6. Recommend levers ONLY from the supplied catalog, and only where they match the diagnosed cause.
7. Populate levers_to_avoid when a lever would be wasteful or margin-destroying — e.g. do not discount a shopper showing no price sensitivity.
8. Set confidence honestly: 'high' when the evidence concentrates on one clear cause, 'low' when it is diffuse or contradictory.
9. If the evidence genuinely does not support any single cause, diagnose UNKNOWN rather than picking the least-bad label. Recommending NO_ACTION is a legitimate, often correct answer — an unnecessary interruption costs more than staying silent.
10. If the cart is empty the shopper is still browsing. Only informational levers make sense; never spend margin on someone who has not chosen anything yet.
11. Write shopper_narrative as plain English a non-technical operator could read aloud, in 2-3 sentences.

Be concise. Stay within these limits so the response fits the token budget:
- supporting_evidence: 3 items maximum
- contributing_factors: 2 items maximum
- recommended_levers: 3 items maximum, ordered by priority (1 = act on first)
- levers_to_avoid: 2 items maximum
- explanation and each rationale: one or two sentences

Respond only with JSON matching the provided schema."""


def build_prompt(
    probability: float,
    risk_tier: str,
    confidence: float,
    features: Dict[str, float],
    evidence: List[Dict[str, Any]],
    cart: CartContext | str,
) -> str:
    """Assemble the case file the agent reasons over."""

    def _shap_lines(items: List[Dict[str, Any]]) -> str:
        return "\n".join(
            f"    - {item['signal']} = {item['observed_value']} "
            f"(SHAP {item['shap_contribution']:+.4f})"
            for item in items
        ) or "    - none"

    pushing = [item for item in evidence if item["shap_contribution"] > 0]
    holding = [item for item in evidence if item["shap_contribution"] <= 0]
    evidence_lines = (
        "  Pushing toward abandonment:\n"
        + _shap_lines(pushing)
        + "\n  Holding the shopper in (these are reassuring, not problems):\n"
        + _shap_lines(holding)
    )

    behaviour = [
        f"  - {statement(name, float(features[name]))}"
        for name in BEHAVIOUR_SIGNALS
        if name in features and informative(name, float(features[name]))
    ]
    behaviour_block = "\n".join(behaviour) or "  - No notable activity recorded yet."

    fact_blocks = []
    for group, names in _FACT_GROUPS.items():
        facts = [
            f"{name}={_value_text(name, float(features[name]))}"
            for name in names
            if name in features
        ]
        if facts:
            fact_blocks.append(f"  {group}: " + "; ".join(facts))

    categories = "\n".join(f"  - {name}: {CATEGORY_DESCRIPTIONS[name]}" for name in ROOT_CAUSE_CATEGORIES)
    cart_description = cart if isinstance(cart, str) else describe_cart(cart)

    return f"""MODEL VERDICT
Abandonment probability: {probability:.1%} (risk tier: {risk_tier})
Model decisiveness: {confidence:.1%}

OBSERVED BEHAVIOUR — what this shopper actually did, this session
{behaviour_block}

SHAP ATTRIBUTION — how the risk model weighted the signals it used
{evidence_lines}

SESSION FACTS
{chr(10).join(fact_blocks)}

CART
{cart_description}

ROOT CAUSE CATEGORIES
{categories}

AVAILABLE INTERVENTION LEVERS
{catalog_for_prompt()}

Diagnose the primary root cause for this specific session."""


def _response_schema() -> Dict[str, Any]:
    """JSON schema handed to Groq for strict structured output.

    Written explicitly rather than derived from pydantic because Groq's strict
    mode requires `additionalProperties: false` on every object and rejects the
    `$defs`/`$ref` indirection that pydantic emits.
    """
    evidence_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "signal": {"type": "string"},
            "observed_value": {"type": "string"},
            "shap_contribution": {"type": "number"},
            "why_it_matters": {"type": "string"},
        },
        "required": ["signal", "observed_value", "shap_contribution", "why_it_matters"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "primary_root_cause": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "category": {"type": "string", "enum": ROOT_CAUSE_CATEGORIES},
                    "headline": {"type": "string"},
                    "explanation": {"type": "string"},
                    "supporting_evidence": {
                        "type": "array",
                        "items": evidence_item,
                        "minItems": 1,
                    },
                },
                "required": ["category", "headline", "explanation", "supporting_evidence"],
            },
            "contributing_factors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "category": {"type": "string", "enum": ROOT_CAUSE_CATEGORIES},
                        "headline": {"type": "string"},
                        "signal": {"type": "string"},
                    },
                    "required": ["category", "headline", "signal"],
                },
            },
            "shopper_narrative": {"type": "string"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "confidence_reasoning": {"type": "string"},
            "recommended_levers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "lever_id": {"type": "string", "enum": LEVER_IDS},
                        "rationale": {"type": "string"},
                        "expected_effect": {"type": "string"},
                        "priority": {"type": "integer"},
                    },
                    "required": ["lever_id", "rationale", "expected_effect", "priority"],
                },
                "minItems": 1,
            },
            "levers_to_avoid": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "lever_id": {"type": "string", "enum": LEVER_IDS},
                        "reason": {"type": "string"},
                    },
                    "required": ["lever_id", "reason"],
                },
            },
        },
        "required": [
            "primary_root_cause",
            "contributing_factors",
            "shopper_narrative",
            "confidence",
            "confidence_reasoning",
            "recommended_levers",
            "levers_to_avoid",
        ],
    }


def call_groq(prompt: str, model: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Compatibility adapter; the shared HTTP client now lives in ``llm``."""

    parsed = GroqClient(model=model).generate_json(
        f"{SYSTEM_PROMPT}\n\n{prompt}",
        _response_schema(),
        config.RCA_MAX_TOKENS,
        config.RCA_TIMEOUT_SECONDS,
    )
    return parsed, {}


def analyse(
    probability: float,
    risk_tier: str,
    confidence: float,
    features: Dict[str, float],
    feature_impacts: Dict[str, float],
    cart: CartContext | str,
    recorder: Any,
) -> Tuple[Optional[RootCauseAnalysis], Dict[str, Any]]:
    """Run the agent. Returns (analysis, metadata).

    `recorder` is a TraceRecorder; the LLM call is wrapped in its own span so the
    console shows model, latency and token usage.
    """
    from ..trace import Stage, Status

    evidence = build_evidence(features, feature_impacts)
    prompt = build_prompt(probability, risk_tier, confidence, features, evidence, cart)

    meta: Dict[str, Any] = {"model_used": None, "latency_ms": 0.0}
    started = time.time()

    # Fallback is opt-in; see config.RCA_FALLBACK_MODEL for why it is off by default.
    candidates = [config.RCA_MODEL]
    if config.RCA_FALLBACK_MODEL:
        candidates.append(config.RCA_FALLBACK_MODEL)

    for attempt, model in enumerate(candidates):
        try:
            with recorder.span(
                Stage.ROOT_CAUSE_AGENT,
                f"LLM root cause analysis ({model})",
            ) as span:
                parsed, usage = call_groq(prompt, model)
                analysis = RootCauseAnalysis.model_validate(parsed)
                meta["model_used"] = model
                meta["latency_ms"] = round((time.time() - started) * 1000, 2)
                span["detail"] = {
                    "model": model,
                    "reasoning_effort": config.RCA_REASONING_EFFORT,
                    "prompt_chars": len(prompt),
                    "evidence_signals": [item["signal"] for item in evidence],
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "primary_cause": analysis.primary_root_cause.category,
                    "confidence": analysis.confidence,
                    "recommended_levers": [
                        lever.lever_id for lever in analysis.recommended_levers
                    ],
                }
                return analysis, meta
        except RateLimitedError as error:
            # Try a fallback model if one is configured, otherwise report the
            # rate limit honestly rather than degrading to invalid output.
            if attempt + 1 < len(candidates):
                recorder.add(
                    Stage.ROOT_CAUSE_AGENT,
                    f"Rate limited on {model}, falling back",
                    status=Status.RATE_LIMITED,
                    detail={"model": model, "error": str(error)},
                )
                continue
            meta["error"] = str(error)
            meta["rate_limited"] = True
            return None, meta
        except Exception as error:  # noqa: BLE001 - surfaced to the caller
            meta["error"] = str(error)
            return None, meta

    return None, meta
