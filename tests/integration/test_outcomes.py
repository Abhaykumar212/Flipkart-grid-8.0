from datetime import datetime, timezone

from backend.domain.events import EventType
from backend.storage.models import InterventionImpression, InterventionOutcome
from tests.event_factories import event_payload


def _create_session(api_harness, session_id: str) -> None:
    response = api_harness.client.post(
        "/api/v1/sessions",
        json={"session_id": session_id, "device_type": "DESKTOP", "referral_source": "DIRECT"},
    )
    assert response.status_code == 201, response.text


def _emit(api_harness, payload: dict) -> None:
    response = api_harness.client.post("/api/v1/events", json=payload)
    assert response.status_code == 202, response.text


def test_impression_is_idempotent_and_order_completion_resolves_outcome(api_harness, monkeypatch) -> None:
    monkeypatch.setattr("backend.config.DECISION_DEBOUNCE_SECONDS", 0)
    session_id = "outcome-treatment"
    _create_session(api_harness, session_id)
    add = event_payload(EventType.ITEM_ADDED_TO_CART, session_id=session_id, sequence_no=1, timestamp=datetime.now(timezone.utc))
    add["product_id"] = "p-1006"
    add["metadata"]["unit_price"] = 8_499
    _emit(api_harness, add)
    _emit(api_harness, event_payload(EventType.CHECKOUT_STARTED, session_id=session_id, sequence_no=2, timestamp=datetime.now(timezone.utc)))
    _emit(api_harness, event_payload(EventType.PAYMENT_FAILED, session_id=session_id, sequence_no=3, timestamp=datetime.now(timezone.utc)))

    decision_response = api_harness.client.post(
        f"/api/v1/sessions/{session_id}/decisions",
        json={"trigger": "PAYMENT_FAILED", "force": True},
    )
    assert decision_response.status_code == 200, decision_response.text
    decision_id = decision_response.json()["decision_id"]

    for _ in range(2):
        response = api_harness.client.post(
            f"/api/v1/decisions/{decision_id}/impression",
            json={"surface": "checkout:CHECKOUT_PANEL"},
        )
        assert response.status_code == 200, response.text

    click = api_harness.client.post(
        f"/api/v1/decisions/{decision_id}/outcome",
        json={"clicked": True},
    )
    assert click.status_code == 200, click.text

    order = event_payload(EventType.ORDER_COMPLETED, session_id=session_id, sequence_no=4, timestamp=datetime.now(timezone.utc))
    order["metadata"]["order_value"] = 8_499
    _emit(api_harness, order)

    with api_harness.sessions() as db:
        impressions = db.query(InterventionImpression).filter_by(decision_id=decision_id).all()
        outcome = db.query(InterventionOutcome).filter_by(decision_id=decision_id).one()
    assert len(impressions) == 1
    assert outcome.clicked is True
    assert outcome.order_completed is True
    assert outcome.time_to_purchase_seconds is not None
    assert outcome.discount_cost == 0
    assert outcome.estimated_margin == round(8_499 * 0.18 - 2, 2)


def test_unknown_decision_outcome_returns_404(api_harness) -> None:
    response = api_harness.client.post(
        "/api/v1/decisions/missing/outcome",
        json={"dismissed": True},
    )
    assert response.status_code == 404
