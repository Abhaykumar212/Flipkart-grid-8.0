"""Catalog of intervention levers available to the recovery system.

This is a **closed set**. The root-cause agent may only recommend levers from
here, which means Phase 3 receives a known, executable vocabulary instead of
free-text suggestions it would have to interpret. Adding a capability to the
product means adding it here first.

Each lever names the friction it addresses, so the agent's recommendation can be
checked against the root cause it diagnosed.
"""

from __future__ import annotations

from typing import Dict, List

# lever_id -> (what it does, which root-cause categories it is appropriate for, cost to business)
LEVER_CATALOG: Dict[str, Dict[str, object]] = {
    "free_delivery_waiver": {
        "description": "Waive the delivery fee on this order.",
        "addresses": ["cost_friction", "delivery_friction"],
        "business_cost": "medium",
    },
    "targeted_discount_code": {
        "description": "Issue a personalised discount code for this cart.",
        "addresses": ["cost_friction"],
        "business_cost": "high",
    },
    "emi_plan_highlight": {
        "description": "Surface No-Cost EMI options prominently for a high-value cart.",
        "addresses": ["cost_friction"],
        "business_cost": "low",
    },
    "price_drop_alert": {
        "description": "Notify the shopper if any cart item drops in price.",
        "addresses": ["cost_friction", "low_intent"],
        "business_cost": "low",
    },
    "delivery_speed_upgrade": {
        "description": "Offer a faster delivery slot, free or discounted.",
        "addresses": ["delivery_friction"],
        "business_cost": "medium",
    },
    "trust_badge_reassurance": {
        "description": "Show secure-payment, return-policy and authenticity guarantees at checkout.",
        "addresses": ["trust_friction"],
        "business_cost": "low",
    },
    "guest_to_account_nudge": {
        "description": "Offer one-tap account creation with a concrete benefit (order tracking, faster reorder).",
        "addresses": ["trust_friction", "checkout_friction"],
        "business_cost": "low",
    },
    "saved_payment_prompt": {
        "description": "Prompt to save a payment method to remove the highest-friction checkout step.",
        "addresses": ["checkout_friction"],
        "business_cost": "low",
    },
    "review_summary_surface": {
        "description": "Surface an AI summary of reviews to resolve product doubt without more research.",
        "addresses": ["product_uncertainty"],
        "business_cost": "low",
    },
    "stock_scarcity_nudge": {
        "description": "Show genuine low-stock or high-demand signals to create urgency.",
        "addresses": ["low_intent", "product_uncertainty"],
        "business_cost": "low",
    },
    "exit_intent_reminder": {
        "description": "Show an on-site reminder when the shopper looks about to leave.",
        "addresses": ["low_intent", "cost_friction", "product_uncertainty"],
        "business_cost": "low",
    },
    "abandoned_cart_email": {
        "description": "Send a follow-up email/notification after the session ends.",
        "addresses": ["low_intent", "cost_friction", "delivery_friction", "trust_friction"],
        "business_cost": "low",
    },
    "checkout_assist_chat": {
        "description": "Offer live assistance when the shopper is stuck mid-checkout.",
        "addresses": ["checkout_friction", "trust_friction"],
        "business_cost": "medium",
    },
    "payment_retry_help": {
        "description": "Detect a failed payment and suggest an alternative method.",
        "addresses": ["checkout_friction"],
        "business_cost": "low",
    },
}

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
