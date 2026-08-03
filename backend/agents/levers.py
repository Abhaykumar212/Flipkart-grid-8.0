"""Catalog of intervention levers available to the recovery system.

This is a **closed set**. The root-cause agent may only recommend levers from
here, which means Phase 3 receives a known, executable vocabulary instead of
free-text suggestions it would have to interpret. Adding a capability to the
product means adding it here first.

Each lever names the friction it addresses, so the agent's recommendation can be
checked against the root cause it diagnosed.

Phase 3 additions
------------------
`expected_conversion_gain` and `cost_score` feed `agents/intervention.py`'s
scoring function. Both are **hackathon assumptions**, not measured lift — same
caveat the repo already applies to synthetic ML metrics: these numbers validate
the ranking mechanics, not a production conversion claim. `fallback_for` names
the safer, lower-cost lever the ranking engine substitutes in when confidence in
the higher-cost primary pick is weak.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# Maps the existing qualitative business_cost onto a 1-3 scale the ranking
# engine can subtract in a weighted sum. Kept as a derivation, not a second
# source of truth, so the two never drift apart.
_COST_SCORE: Dict[str, int] = {"low": 1, "medium": 2, "high": 3}

# lever_id -> (what it does, which root-cause categories it is appropriate for, cost to business)
LEVER_CATALOG: Dict[str, Dict[str, object]] = {
    "free_delivery_waiver": {
        "description": "Waive the delivery fee on this order.",
        "addresses": ["cost_friction", "delivery_friction"],
        "business_cost": "medium",
        "expected_conversion_gain": 0.22,
        "fallback_for": "targeted_discount_code",
    },
    "targeted_discount_code": {
        "description": "Issue a personalised discount code for this cart.",
        "addresses": ["cost_friction"],
        "business_cost": "high",
        "expected_conversion_gain": 0.30,
        "fallback_for": None,
    },
    "emi_plan_highlight": {
        "description": "Surface No-Cost EMI options prominently for a high-value cart.",
        "addresses": ["cost_friction"],
        "business_cost": "low",
        "expected_conversion_gain": 0.18,
        "fallback_for": "targeted_discount_code",
    },
    "price_drop_alert": {
        "description": "Notify the shopper if any cart item drops in price.",
        "addresses": ["cost_friction", "low_intent"],
        "business_cost": "low",
        "expected_conversion_gain": 0.12,
        "fallback_for": "targeted_discount_code",
    },
    "delivery_speed_upgrade": {
        "description": "Offer a faster delivery slot, free or discounted.",
        "addresses": ["delivery_friction"],
        "business_cost": "medium",
        "expected_conversion_gain": 0.20,
        "fallback_for": None,
    },
    "trust_badge_reassurance": {
        "description": "Show secure-payment, return-policy and authenticity guarantees at checkout.",
        "addresses": ["trust_friction"],
        "business_cost": "low",
        "expected_conversion_gain": 0.14,
        "fallback_for": None,
    },
    "guest_to_account_nudge": {
        "description": "Offer one-tap account creation with a concrete benefit (order tracking, faster reorder).",
        "addresses": ["trust_friction", "checkout_friction"],
        "business_cost": "low",
        "expected_conversion_gain": 0.15,
        "fallback_for": "trust_badge_reassurance",
    },
    "saved_payment_prompt": {
        "description": "Prompt to save a payment method to remove the highest-friction checkout step.",
        "addresses": ["checkout_friction"],
        "business_cost": "low",
        "expected_conversion_gain": 0.17,
        "fallback_for": None,
    },
    "review_summary_surface": {
        "description": "Surface an AI summary of reviews to resolve product doubt without more research.",
        "addresses": ["product_uncertainty"],
        "business_cost": "low",
        "expected_conversion_gain": 0.19,
        "fallback_for": None,
    },
    "stock_scarcity_nudge": {
        "description": "Show genuine low-stock or high-demand signals to create urgency.",
        "addresses": ["low_intent", "product_uncertainty"],
        "business_cost": "low",
        "expected_conversion_gain": 0.13,
        "fallback_for": None,
    },
    "exit_intent_reminder": {
        "description": "Show an on-site reminder when the shopper looks about to leave.",
        "addresses": ["low_intent", "cost_friction", "product_uncertainty"],
        "business_cost": "low",
        "expected_conversion_gain": 0.11,
        "fallback_for": None,
    },
    "abandoned_cart_email": {
        "description": "Send a follow-up email/notification after the session ends.",
        "addresses": ["low_intent", "cost_friction", "delivery_friction", "trust_friction"],
        "business_cost": "low",
        "expected_conversion_gain": 0.10,
        "fallback_for": None,
    },
    "checkout_assist_chat": {
        "description": "Offer live assistance when the shopper is stuck mid-checkout.",
        "addresses": ["checkout_friction", "trust_friction"],
        "business_cost": "medium",
        "expected_conversion_gain": 0.21,
        "fallback_for": "saved_payment_prompt",
    },
    "payment_retry_help": {
        "description": "Detect a failed payment and suggest an alternative method.",
        "addresses": ["checkout_friction"],
        "business_cost": "low",
        "expected_conversion_gain": 0.24,
        "fallback_for": None,
    },
}

for _meta in LEVER_CATALOG.values():
    _meta["cost_score"] = _COST_SCORE[_meta["business_cost"]]  # type: ignore[index]

LEVER_IDS: List[str] = list(LEVER_CATALOG)

ROOT_CAUSE_CATEGORIES: List[str] = [
    "cost_friction",
    "delivery_friction",
    "trust_friction",
    "checkout_friction",
    "product_uncertainty",
    "low_intent",
]

CATEGORY_DESCRIPTIONS: Dict[str, str] = {
    "cost_friction": "Total cost — basket size, delivery fees or a missing discount — is the barrier.",
    "delivery_friction": "Delivery speed, date or serviceability is the barrier.",
    "trust_friction": "Confidence in the platform, seller or payment security is the barrier.",
    "checkout_friction": "The mechanics of completing the order are the barrier (failed payment, no saved card, guest flow, funnel depth).",
    "product_uncertainty": "The shopper is unsure the product itself is right — still researching or comparing.",
    "low_intent": "There is no specific blocker; the session simply lacks purchase intent.",
}


# Nominal assumed give-away value per rung-3 (margin-spending) lever, INR. Same
# hackathon caveat as `expected_conversion_gain` above: an assumption, not a
# measured cost. Used only to make the session ledger's "promotional spend
# avoided" arithmetic visible.
#
# Deliberately duplicated from `RUNG3_ASSUMED_VALUE_INR` in
# `src/lib/interventionPolicy.ts` — the client needs it to render the panel live,
# the server needs it to rebuild the same numbers after a reload. Keep the two
# in step; `tests/test_persistence.py` pins the values on this side.
RUNG3_ASSUMED_VALUE_INR: Dict[str, int] = {
    "targeted_discount_code": 200,
    "free_delivery_waiver": 40,
    "delivery_speed_upgrade": 60,
}


def catalog_for_prompt() -> str:
    """Compact rendering of the catalog for inclusion in the agent prompt."""
    lines = []
    for lever_id, meta in LEVER_CATALOG.items():
        addresses = ", ".join(meta["addresses"])  # type: ignore[arg-type]
        lines.append(
            f"- {lever_id} (cost: {meta['business_cost']}) — {meta['description']} "
            f"Appropriate for: {addresses}."
        )
    return "\n".join(lines)
