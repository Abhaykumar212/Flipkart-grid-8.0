"""Phase 2 — root cause analysis agent.

Given the Phase 1 model's prediction *and its SHAP attribution*, plus the actual
cart contents, this agent produces structured JSON naming why the cart is at
risk and which intervention levers fit.

Design intent
-------------
The agent explains **the model's own attribution**. Its evidence array is built
from SHAP values, not from free association over a prompt, so it cannot name a
cause the model did not attribute. That property is what makes the output
defensible: "the LLM isn't guessing, it's verbalising the model's reasoning."

The response is enforced by the active provider's structured-output mode
(Groq's strict `json_schema`, or Gemini's `response_schema`) and re-validated
locally with pydantic, so a downstream phase never has to parse free text.
`config.LLM_PROVIDER` selects which one is live.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .. import config
from ..schemas import CartContext, RootCauseAnalysis
from .levers import (
    CATEGORY_DESCRIPTIONS,
    LEVER_IDS,
    ROOT_CAUSE_CATEGORIES,
    catalog_for_prompt,
)

# Human labels for the raw model features. Mirrors the frontend inspector so the
# same vocabulary appears in the UI, the prompt and the analysis.
FEATURE_LABELS: Dict[str, str] = {
    "seconds_spent_in_cart": "time spent in cart",
    "times_returned_to_product_page": "returns to the product page",
    "product_reviews_read": "product reviews read",
    "seconds_idle_before_checkout": "idle time before checkout",
    "delivery_pincode_checks": "delivery pincode checks",
    "saved_items_in_wishlist": "items saved in wishlist",
    "cart_value_vs_typical_order": "cart value vs this shopper's usual order",
    "delivery_fee_percent_of_cart": "delivery fee as % of cart",
    "price_dropped_since_first_view": "price dropped since first view",
    "discount_seeking_tendency": "discount-seeking tendency",
    "failed_coupon_attempts": "failed coupon attempts",
    "estimated_delivery_days": "estimated delivery days",
    "payment_method_on_file": "saved payment method",
    "checkout_steps_completed": "checkout steps completed (of 3)",
    "payment_attempts_failed": "failed payment attempts",
    "is_guest_checkout": "guest checkout",
    "past_abandonment_rate": "historical abandonment rate",
    "past_order_return_rate": "historical return rate",
    "lifetime_orders_placed": "lifetime orders placed",
    "days_since_last_purchase": "days since last purchase",
    "is_mobile_session": "mobile session",
    "is_late_night_session": "late-night session",
    # Engineered
    "extra_cost_burden_score": "combined delivery-fee and basket-size burden",
    "product_research_intensity": "product research intensity",
    "checkout_friction_events": "count of checkout blockers hit",
    "delivery_concern_index": "delivery concern index",
    "dwell_per_return_visit": "dwell time per return visit",
    "hesitation_ratio": "share of cart time spent idle",
    "price_sensitivity_exposure": "price sensitivity against basket size",
    "customer_loyalty_score": "loyalty score (frequency damped by recency)",
    "checkout_progress_ratio": "fraction of checkout funnel completed",
    "trust_barrier_score": "guest checkout on a high-value basket",
}

# Feature subset that materially changes the diagnosis. Used for dedup hashing
# so trivial dwell-time drift doesn't re-trigger an identical analysis.
MATERIAL_FEATURES: Tuple[str, ...] = (
    "cart_value_vs_typical_order",
    "delivery_fee_percent_of_cart",
    "estimated_delivery_days",
    "payment_method_on_file",
    "checkout_steps_completed",
    "payment_attempts_failed",
    "is_guest_checkout",
    "failed_coupon_attempts",
    "times_returned_to_product_page",
    "product_reviews_read",
    "price_dropped_since_first_view",
)

# Features the *diagnosis* is allowed to cite as evidence. Prediction (the
# XGBoost model + its full SHAP attribution) keeps using every feature,
# including funnel progress — that's what it's good at. Diagnosis is a
# narrower question: not "how likely is this cart to convert" but "why is
# *this* shopper hesitating", and a handful of features answer a different
# question than that.
#
# `checkout_steps_completed`/`checkout_progress_ratio` are pure funnel
# position, not a friction event — a shopper who hasn't started checkout yet
# looks the same on these features whether the barrier is cost, delivery,
# trust or nothing at all, so they carry no information about *cause*.
# `payment_method_on_file` is a static demo placeholder (see MODEL_CARD.md
# limitation #2 — it never varies with live session behaviour) and, per
# `ml/artifacts/model.joblib`'s own gain ranking, the single highest-gain
# feature in the model; left in, it and `checkout_steps_completed` swamp every
# other signal's SHAP magnitude regardless of scenario, which is exactly the
# collapse-to-checkout_friction bug this subset exists to fix.
# `checkout_friction_events` is excluded because it's a sum that embeds
# `payment_method_on_file` as one of its four terms, reintroducing the same
# swamping feature by another name; its genuinely diagnostic components
# (`payment_attempts_failed`, `failed_coupon_attempts`) are already included
# individually below. Generic profile/context features
# (`customer_loyalty_score`, `lifetime_orders_placed`,
# `days_since_last_purchase`, `saved_items_in_wishlist`, `is_mobile_session`,
# `is_late_night_session`) describe who the shopper is or when they're
# shopping, not why this cart is at risk, so they're left out too.
# `extra_cost_burden_score` is excluded because delivery is free on every
# cart in this catalog above the ₹500 free-delivery threshold, so the feature
# is a near-constant that only ever reflects `cart_value_vs_typical_order`
# restated, not a distinct cost signal.
DIAGNOSTIC_FEATURE_NAMES: Tuple[str, ...] = (
    # Cost / price-comparison signals
    "cart_value_vs_typical_order",
    "delivery_fee_percent_of_cart",
    "price_dropped_since_first_view",
    "discount_seeking_tendency",
    "failed_coupon_attempts",
    "price_sensitivity_exposure",
    # Delivery signals
    "estimated_delivery_days",
    "delivery_pincode_checks",
    "delivery_concern_index",
    # Checkout / trust signals that are concrete events or states, not funnel position
    "payment_attempts_failed",
    "is_guest_checkout",
    "trust_barrier_score",
    # Engagement / research signals
    "seconds_spent_in_cart",
    "times_returned_to_product_page",
    "product_reviews_read",
    "seconds_idle_before_checkout",
    "product_research_intensity",
    "dwell_per_return_visit",
    "hesitation_ratio",
    # Prior behaviour
    "past_abandonment_rate",
    "past_order_return_rate",
)


def _format_value(name: str, value: float) -> str:
    """Render a feature value the way a human would describe it."""
    booleans = {
        "price_dropped_since_first_view",
        "payment_method_on_file",
        "is_guest_checkout",
        "is_mobile_session",
        "is_late_night_session",
    }
    if name in booleans:
        return "yes" if value >= 0.5 else "no"
    if name in {"past_abandonment_rate", "discount_seeking_tendency", "past_order_return_rate"}:
        return f"{value * 100:.0f}%"
    if name == "cart_value_vs_typical_order":
        return f"{value:.2f}x their usual order"
    if name == "delivery_fee_percent_of_cart":
        return f"{value:.1f}% of cart value"
    if name in {"seconds_spent_in_cart", "seconds_idle_before_checkout"}:
        return f"{value:.0f}s"
    if name == "estimated_delivery_days":
        return f"{value:.0f} days"
    if name == "checkout_steps_completed":
        return f"{value:.0f} of 3 steps"
    if name == "days_since_last_purchase":
        return f"{value:.0f} days ago"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.3f}"


def build_feature_signature(features: Dict[str, float]) -> str:
    """Stable hash of the diagnosis-relevant features, for dedup."""
    parts = [f"{name}={round(float(features.get(name, 0)), 3)}" for name in MATERIAL_FEATURES]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def build_evidence(
    features: Dict[str, float],
    feature_impacts: Dict[str, float],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Top signed SHAP contributors, rendered for the prompt.

    Positive SHAP pushes toward abandonment, negative pulls toward conversion.
    Both directions are included: knowing what is *holding the shopper in* is as
    useful for choosing a lever as knowing what is pushing them away.

    Ranked over `DIAGNOSTIC_FEATURE_NAMES` only, not the full 32-feature
    attribution `_run_inference` computes. Funnel-progress features
    (`checkout_steps_completed`, `payment_method_on_file`, ...) are the
    model's highest-gain features and dominate the *prediction* correctly,
    but including them here meant the diagnosis collapsed to
    "checkout_friction" on almost every session regardless of what was
    actually driving hesitation — see the comment on
    `DIAGNOSTIC_FEATURE_NAMES` above.
    """
    diagnostic_impacts = {
        name: impact for name, impact in feature_impacts.items() if name in DIAGNOSTIC_FEATURE_NAMES
    }
    ranked = sorted(diagnostic_impacts.items(), key=lambda kv: abs(kv[1]), reverse=True)[:limit]
    evidence = []
    for name, impact in ranked:
        raw_value = features.get(name)
        evidence.append(
            {
                "signal": name,
                "label": FEATURE_LABELS.get(name, name),
                "observed_value": _format_value(name, float(raw_value)) if raw_value is not None else "derived",
                "shap_contribution": round(float(impact), 4),
                "direction": "increases abandonment risk" if impact > 0 else "reduces abandonment risk",
            }
        )
    return evidence


def _describe_cart(cart: CartContext) -> str:
    if not cart.lines:
        return "Cart contents were not supplied."
    rows = []
    for line in cart.lines:
        bits = [
            f"{line.quantity}x {line.title}",
            f"₹{line.selling_price:,.0f}",
        ]
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


SYSTEM_PROMPT = """You are a cart-abandonment root cause analyst for an Indian e-commerce platform.

A gradient-boosted model has already scored this session's abandonment risk and produced SHAP attributions showing exactly which signals drove that score. Your job is to explain WHY, grounded strictly in that attribution.

Rules:
1. Your diagnosis must be supported by the SHAP evidence provided. Do not invent causes that the evidence does not support.
2. Positive SHAP values push toward abandonment; negative values pull toward conversion. Weigh both.
2b. The SHAP evidence you are given is deliberately restricted to behavioural and cost/delivery/trust signals that explain WHY a shopper hesitates. Checkout-funnel-progress facts (how many of the 3 checkout steps are done, whether a payment method is on file) are intentionally withheld from the evidence array — they tell you HOW FAR a shopper got and how risky the session is, not WHY, and are not valid support for a root cause. You may still see them quoted as plain facts under SESSION FACTS for context; do not cite them as evidence for `primary_root_cause` or `contributing_factors`.
3. Quote concrete observed values (amounts, counts, days) in your explanation — be specific, not generic.
4. Recommend levers ONLY from the supplied catalog, and only where they match the diagnosed cause.
5. Populate levers_to_avoid when a lever would be wasteful or margin-destroying — e.g. do not discount a shopper showing no price sensitivity.
6. Set confidence honestly: 'high' when the evidence concentrates on one clear cause, 'low' when it is diffuse or contradictory.
7. Write shopper_narrative as plain English a non-technical operator could read aloud, in 2-3 sentences.

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
    cart: CartContext,
) -> str:
    """Assemble the case file the agent reasons over."""
    evidence_lines = "\n".join(
        f"  - {item['label']} ({item['signal']}): observed {item['observed_value']}, "
        f"SHAP {item['shap_contribution']:+.4f} — {item['direction']}"
        for item in evidence
    )

    grouped = {
        "Cost signals": [
            "cart_value_vs_typical_order",
            "delivery_fee_percent_of_cart",
            "discount_seeking_tendency",
            "failed_coupon_attempts",
            "price_dropped_since_first_view",
        ],
        "Delivery signals": ["estimated_delivery_days", "delivery_pincode_checks"],
        "Checkout & trust signals": [
            "payment_method_on_file",
            "checkout_steps_completed",
            "payment_attempts_failed",
            "is_guest_checkout",
        ],
        "Engagement signals": [
            "seconds_spent_in_cart",
            "times_returned_to_product_page",
            "product_reviews_read",
            "seconds_idle_before_checkout",
        ],
        "Shopper history": [
            "past_abandonment_rate",
            "lifetime_orders_placed",
            "days_since_last_purchase",
            "past_order_return_rate",
        ],
        "Session context": ["is_mobile_session", "is_late_night_session"],
    }
    fact_blocks = []
    for group, names in grouped.items():
        facts = [
            f"{FEATURE_LABELS.get(n, n)}: {_format_value(n, float(features[n]))}"
            for n in names
            if n in features
        ]
        if facts:
            fact_blocks.append(f"{group}: " + "; ".join(facts))

    categories = "\n".join(f"  - {c}: {CATEGORY_DESCRIPTIONS[c]}" for c in ROOT_CAUSE_CATEGORIES)

    return f"""MODEL VERDICT
Abandonment probability: {probability:.1%} (risk tier: {risk_tier})
Model decisiveness: {confidence:.1%}

SHAP ATTRIBUTION — the model's own reasoning, ranked by magnitude
{evidence_lines}

SESSION FACTS
{chr(10).join('  ' + block for block in fact_blocks)}

CART
{_describe_cart(cart)}

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


class RateLimitedError(RuntimeError):
    """The provider returned 429. Distinguished so the caller can degrade, not fail."""


def _strip_for_gemini(schema: Any) -> Any:
    """Gemini's schema proto has no `additionalProperties`/`minItems` fields —
    only `type_, format_, description, nullable, enum, items, max_items,
    properties, required`. `_response_schema()` is written for Groq's strict
    json_schema mode, which needs `additionalProperties: false`; this strips
    what Gemini doesn't understand rather than maintaining a second schema.
    """
    if isinstance(schema, dict):
        cleaned = {k: v for k, v in schema.items() if k not in ("additionalProperties", "minItems")}
        return {k: _strip_for_gemini(v) for k, v in cleaned.items()}
    if isinstance(schema, list):
        return [_strip_for_gemini(item) for item in schema]
    return schema


def call_gemini(
    prompt: str,
    model: str,
    system_prompt: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None,
    max_tokens: Optional[int] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Call Gemini with structured JSON output. Returns (parsed, usage)."""
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions

    genai.configure(api_key=config.GEMINI_API_KEY)
    gen_model = genai.GenerativeModel(
        model_name=model, system_instruction=system_prompt or SYSTEM_PROMPT
    )

    try:
        response = gen_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=config.RCA_TEMPERATURE,
                max_output_tokens=max_tokens or config.RCA_MAX_TOKENS,
                response_mime_type="application/json",
                response_schema=schema if schema is not None else _strip_for_gemini(_response_schema()),
            ),
            request_options={"timeout": config.RCA_TIMEOUT_SECONDS},
        )
    except google_exceptions.ResourceExhausted as error:
        raise RateLimitedError(str(error)) from error
    except google_exceptions.GoogleAPIError as error:
        raise RuntimeError(f"Gemini error: {error}") from error

    usage_meta = getattr(response, "usage_metadata", None)
    usage = {
        "prompt_tokens": getattr(usage_meta, "prompt_token_count", None),
        "completion_tokens": getattr(usage_meta, "candidates_token_count", None),
    }
    return json.loads(response.text), usage


def call_llm(
    prompt: str,
    model: str,
    system_prompt: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None,
    schema_name: str = "root_cause_analysis",
    max_tokens: Optional[int] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Dispatches to whichever provider `config.LLM_PROVIDER` selects.

    The optional arguments exist so `agents/critic.py` can borrow this
    provider dispatch — and its rate-limit handling — for a different prompt and
    schema. Omitted, every one of them falls back to the RCA call this function
    was written for, so existing callers are untouched.
    """
    if config.LLM_PROVIDER == "gemini":
        return call_gemini(prompt, model, system_prompt, schema, max_tokens)
    return call_groq(prompt, model, system_prompt, schema, schema_name, max_tokens)


def call_groq(
    prompt: str,
    model: str,
    system_prompt: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None,
    schema_name: str = "root_cause_analysis",
    max_tokens: Optional[int] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """POST to Groq with strict schema enforcement. Returns (parsed, usage)."""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.RCA_TEMPERATURE,
        "max_tokens": max_tokens or config.RCA_MAX_TOKENS,
        "reasoning_effort": config.RCA_REASONING_EFFORT,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": schema if schema is not None else _response_schema(),
            },
        },
    }
    request = urllib.request.Request(
        f"{config.GROQ_BASE_URL}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.GROQ_API_KEY}",
            "Content-Type": "application/json",
            # Groq sits behind Cloudflare, which rejects Python's default
            # urllib User-Agent with a 403.
            "User-Agent": "flipkart-grid-rca/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=config.RCA_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            detail = json.loads(error.read()).get("error", {}).get("message", "")
        except Exception:
            pass
        if error.code == 429:
            raise RateLimitedError(detail or "Groq rate limit reached") from error
        raise RuntimeError(f"Groq HTTP {error.code}: {detail}") from error

    content = payload["choices"][0]["message"]["content"]
    return json.loads(content), payload.get("usage", {})


def analyse(
    probability: float,
    risk_tier: str,
    confidence: float,
    features: Dict[str, float],
    feature_impacts: Dict[str, float],
    cart: CartContext,
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

    # Fallback is opt-in and Groq-specific; see config.RCA_FALLBACK_MODEL for why
    # it is off by default. Gemini has no configured fallback model yet.
    candidates = [config.RCA_MODEL]
    if config.LLM_PROVIDER == "groq" and config.RCA_FALLBACK_MODEL:
        candidates.append(config.RCA_FALLBACK_MODEL)

    for attempt, model in enumerate(candidates):
        try:
            with recorder.span(
                Stage.ROOT_CAUSE_AGENT,
                f"LLM root cause analysis ({model})",
            ) as span:
                parsed, usage = call_llm(prompt, model)
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
