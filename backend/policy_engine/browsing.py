"""When a shopper with no cart still deserves help.

The risk model is defined over sessions that have a cart — it is trained on
cart abandonment, and `risk_model.predict` deliberately clamps a cart-less
session to a low probability rather than extrapolating. That honesty has a
cost: a shopper who has read the same reviews four times and compared three
products is visibly stuck, and the intervention floor would ignore them
entirely because there is nothing in their basket yet.

So browsing assistance is judged on **observed deliberation**, not on
abandonment probability, and it is deliberately cheap-only. A shopper who has
not chosen anything cannot be sold a discount; the most they can be offered is
information they were already looking for. `is_browsing_assist` says the
shopper qualifies, `permits` says a given candidate is modest enough to run.
"""

from __future__ import annotations

from backend.domain.enums import CostLevel
from backend.domain.interventions import InterventionDefinition, InterventionId

#: Any one of these, with an empty cart, counts as deliberation.
MIN_REVIEW_DWELL_SECONDS = 20.0
MIN_REVIEW_OPENS = 2
MIN_COMPARISONS = 1
MIN_SIMILAR_VIEWS = 3

#: Browsing help must be free and quiet. Intrusiveness 1 is an inline card or a
#: banner; 2 and 3 take over the page, which is not earned by browsing alone.
MAX_COST = (CostLevel.ZERO, CostLevel.LOW)
MAX_INTRUSIVENESS = 1


def is_browsing_assist(features: dict[str, float]) -> bool:
    """Empty cart, but the shopper is visibly deliberating."""

    if features.get("c_item_count", 0.0) > 0:
        return False
    return (
        features.get("s_review_dwell_seconds", 0.0) >= MIN_REVIEW_DWELL_SECONDS
        or features.get("s_review_open_count", 0.0) >= MIN_REVIEW_OPENS
        or features.get("s_comparison_count", 0.0) >= MIN_COMPARISONS
        or features.get("s_similar_product_view_count", 0.0) >= MIN_SIMILAR_VIEWS
    )


def permits(candidate: InterventionDefinition) -> bool:
    """Whether this candidate is modest enough to show a browsing shopper."""

    if candidate.intervention_id == InterventionId.NO_ACTION:
        return True
    return (
        candidate.cost_level in MAX_COST
        and candidate.intrusiveness <= MAX_INTRUSIVENESS
    )
