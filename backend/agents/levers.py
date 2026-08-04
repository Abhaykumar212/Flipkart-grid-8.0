"""The vocabulary the LLM agent is allowed to speak, derived from the runtime.

This used to be a hand-maintained catalog with its own cause names and lever
ids, which meant every agent response had to be translated before the policy
engine could act on it. It is now **derived** from the two things that actually
execute: `domain/causes.py` for the diagnosis vocabulary and
`recommendation/catalogue.py` for what the delivery layer can render.

The point is that the agent cannot name a cause the models don't emit, or a
lever the policy engine has never heard of — the strict `json_schema` enum is
built from these lists, so a hallucinated identifier is rejected at the API
boundary rather than downstream. Adding an intervention to the catalogue offers
it to the agent automatically.

`UNKNOWN` and `NO_ACTION` are deliberately included. An agent that cannot say
"I don't know" or "leave them alone" will invent a cause to justify acting.
"""

from __future__ import annotations

from typing import Dict, List

from ..domain.causes import RootCause
from ..domain.enums import CostLevel
from ..domain.interventions import InterventionId
from ..explainability.templates import CAUSE_STATEMENTS
from ..recommendation.catalogue import INTERVENTION_CATALOGUE

# Operator-facing summaries of what each lever *does*. The shopper-facing copy
# in `INTERVENTION_COPY` is written to be read by a customer; the agent needs to
# know the mechanism and its business cost to choose between levers.
LEVER_DESCRIPTIONS: Dict[InterventionId, str] = {
    InterventionId.REVIEW_SUMMARY: "Surface a grounded summary of real customer reviews so the shopper can resolve product doubt without more research.",
    InterventionId.PRODUCT_COMPARISON: "Show a side-by-side comparison of the products the shopper has been weighing up.",
    InterventionId.DELIVERY_REASSURANCE: "Restate the concrete delivery date, fee and serviceability for this cart.",
    InterventionId.RETURN_POLICY_REASSURANCE: "Show the return, replacement and authenticity protections that apply.",
    InterventionId.PRICE_DROP_ALERT: "Offer to watch the price and notify the shopper if it falls. Costs no margin now.",
    InterventionId.SIMILAR_PRODUCT_RECOMMENDATION: "Recommend well-rated in-stock alternatives without disturbing the current cart.",
    InterventionId.EMI_SUGGESTION: "Surface eligible EMI plans so a high-value basket can be paid monthly.",
    InterventionId.ALTERNATE_PAYMENT_METHOD: "After a failed payment, offer a different payment route to complete the order NOW. This is the correct first response to any declined or failed payment.",
    InterventionId.CHECKOUT_ASSISTANCE: "Offer guidance through the remaining checkout steps when the shopper is stuck.",
    InterventionId.WISHLIST_REMINDER: "Offer to save the items for later so the session ends without losing the basket.",
    InterventionId.LIMITED_TIME_DISCOUNT: "Issue a genuine time-boxed discount on this cart. This spends margin — only justified by verified price sensitivity.",
    InterventionId.STOCK_SCARCITY_NUDGE: "State genuine remaining stock. Only ever used when the stock signal is real; never manufacture urgency.",
    InterventionId.EXIT_INTENT_REMINDER: "Catch a shopper who looks about to leave and reassure them their selection is saved.",
    InterventionId.TRUST_BADGE_REASSURANCE: "Show secure-payment, verified-seller and replacement-window guarantees.",
    InterventionId.SAVED_PAYMENT_PROMPT: "Offer to store a payment method to speed up FUTURE checkouts. It does not recover a payment that has just failed — prefer ALTERNATE_PAYMENT_METHOD for that, and treat this only as a follow-up.",
    InterventionId.GUEST_ACCOUNT_NUDGE: "Offer one-tap account creation with a concrete benefit — order tracking and faster reorder.",
    InterventionId.DELIVERY_SPEED_UPGRADE: "Offer an earlier delivery slot. This spends margin — only justified by a genuine delivery concern.",
    InterventionId.FREE_DELIVERY_WAIVER: "Waive the delivery fee on this order. This spends margin — only justified when the fee itself is the barrier.",
    InterventionId.NO_ACTION: "Deliberately show the shopper nothing. The correct choice when evidence is weak, diffuse, or the shopper is already converting.",
}

_COST_WORD: Dict[CostLevel, str] = {
    CostLevel.ZERO: "none",
    CostLevel.LOW: "low",
    CostLevel.MEDIUM: "medium",
    CostLevel.HIGH: "high",
}

#: Diagnosis vocabulary, including UNKNOWN so the agent can abstain honestly.
ROOT_CAUSE_CATEGORIES: List[str] = [cause.value for cause in RootCause]

CATEGORY_DESCRIPTIONS: Dict[str, str] = {
    cause.value: CAUSE_STATEMENTS[cause] for cause in RootCause
}

LEVER_CATALOG: Dict[str, Dict[str, object]] = {
    item.intervention_id.value: {
        "description": LEVER_DESCRIPTIONS.get(
            item.intervention_id, item.display_name
        ),
        "addresses": [
            cause.value if isinstance(cause, RootCause) else str(cause)
            for cause in item.supported_causes
        ],
        "business_cost": _COST_WORD[item.cost_level],
        "intrusiveness": item.intrusiveness,
    }
    for item in INTERVENTION_CATALOGUE
}

LEVER_IDS: List[str] = list(LEVER_CATALOG)


def catalog_for_prompt() -> str:
    """Compact rendering of the catalog for inclusion in the agent prompt."""
    lines = []
    for lever_id, meta in LEVER_CATALOG.items():
        addresses = ", ".join(meta["addresses"])  # type: ignore[arg-type]
        scope = "any cause" if addresses == "*" else f"Appropriate for: {addresses}."
        lines.append(
            f"- {lever_id} (business cost: {meta['business_cost']}) — "
            f"{meta['description']} {scope}"
        )
    return "\n".join(lines)
