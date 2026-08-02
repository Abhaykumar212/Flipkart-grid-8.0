from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.domain.causes import EVIDENCE_FAMILIES, RootCause
from backend.domain.events import EventEnvelope, EventType
from backend.domain.interventions import InterventionId
from backend.recommendation.catalogue import INTERVENTION_CATALOGUE


def test_frozen_domain_cardinalities():
    assert len(EventType) == 21
    assert len(RootCause) == 11
    assert len(InterventionId) == 12
    assert len(INTERVENTION_CATALOGUE) == 12
    assert set(EVIDENCE_FAMILIES) == set(RootCause)


def test_every_cause_has_a_supporting_intervention():
    supported = {
        cause
        for intervention in INTERVENTION_CATALOGUE
        for cause in intervention.supported_causes
        if cause != "*"
    }
    assert supported == set(RootCause) - {RootCause.UNKNOWN}
    assert any("*" in intervention.supported_causes for intervention in INTERVENTION_CATALOGUE)


def test_catalogue_matches_the_frozen_contract():
    actual = {
        item.intervention_id.value: (
            tuple(cause.value if hasattr(cause, "value") else cause for cause in item.supported_causes),
            item.cost_level.value,
            item.intrusiveness,
            item.cooldown_minutes,
            tuple(channel.value for channel in item.allowed_channels),
            item.requires,
            item.prior_uplift,
        )
        for item in INTERVENTION_CATALOGUE
    }
    assert actual == {
        "REVIEW_SUMMARY": (("PRODUCT_QUALITY_UNCERTAINTY",), "LOW", 1, 15, ("INLINE_CARD", "ASSISTANT_PANEL"), ("review_summary_available",), 0.28),
        "PRODUCT_COMPARISON": (("CHOICE_OVERLOAD",), "LOW", 1, 15, ("COMPARISON_DRAWER", "ASSISTANT_PANEL"), ("≥2_comparable_products",), 0.26),
        "DELIVERY_REASSURANCE": (("DELIVERY_CONCERN",), "LOW", 1, 10, ("INLINE_CARD", "BANNER"), ("delivery_data_available",), 0.27),
        "RETURN_POLICY_REASSURANCE": (("TRUST_OR_RETURN_POLICY_CONCERN",), "LOW", 1, 20, ("INLINE_CARD", "ASSISTANT_PANEL"), (), 0.19),
        "PRICE_DROP_ALERT": (("PRICE_SENSITIVITY",), "LOW", 1, 20, ("INLINE_CARD", "BANNER"), ("price_history_available",), 0.24),
        "SIMILAR_PRODUCT_RECOMMENDATION": (("PRICE_SENSITIVITY", "PRODUCT_AVAILABILITY_CONCERN"), "LOW", 2, 20, ("COMPARISON_DRAWER", "INLINE_CARD"), ("≥3_similar_in_stock",), 0.21),
        "EMI_SUGGESTION": (("AFFORDABILITY_OR_EMI_NEED",), "LOW", 1, 30, ("INLINE_CARD", "CHECKOUT_PANEL"), ("emi_eligible", "cart_value≥5000"), 0.25),
        "ALTERNATE_PAYMENT_METHOD": (("CHECKOUT_OR_PAYMENT_FAILURE",), "LOW", 1, 5, ("CHECKOUT_PANEL",), ("payment_failure_occurred",), 0.33),
        "CHECKOUT_ASSISTANCE": (("CHECKOUT_OR_PAYMENT_FAILURE",), "LOW", 2, 10, ("CHECKOUT_PANEL", "ASSISTANT_PANEL"), ("checkout_started",), 0.22),
        "WISHLIST_REMINDER": (("LOW_PURCHASE_INTENT", "SESSION_INTERRUPTION_OR_DISTRACTION"), "LOW", 1, 30, ("BANNER", "INLINE_CARD"), (), 0.14),
        "LIMITED_TIME_DISCOUNT": (("PRICE_SENSITIVITY",), "HIGH", 3, 60, ("INLINE_CARD", "BANNER"), ("discount_budget_available", "cart_value≥1000"), 0.38),
        "NO_ACTION": (("*",), "ZERO", 0, 0, (), (), 0.0),
    }


def test_event_metadata_is_validated_by_event_type():
    envelope = EventEnvelope.model_validate({
        "event_id": str(uuid4()),
        "event_type": "ITEM_ADDED_TO_CART",
        "session_id": "session-1",
        "product_id": "p-1001",
        "sequence_no": 1,
        "client_timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {"quantity": 1, "unit_price": 71999},
    })
    assert envelope.metadata.quantity == 1

    with pytest.raises(ValidationError):
        EventEnvelope.model_validate({
            "event_id": str(uuid4()),
            "event_type": "ITEM_ADDED_TO_CART",
            "session_id": "session-1",
            "sequence_no": 1,
            "client_timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {"quantity": 1, "unit_price": 71999},
        })


def test_unknown_event_type_is_rejected():
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate({
            "event_id": str(uuid4()),
            "event_type": "MADE_UP_EVENT",
            "session_id": "session-1",
            "sequence_no": 1,
            "client_timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        })
