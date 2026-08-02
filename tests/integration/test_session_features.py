from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from backend.domain.events import EventType
from backend.feature_engine.schema import FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from backend.storage.models import (
    Order,
    SessionFeatureSnapshot,
    ShoppingSession,
    User,
)
from backend.storage.repositories import user_history
from tests.event_factories import event_payload

def test_session_get_returns_features_and_persists_one_snapshot_per_request(api_harness):
    session_id = "feature-snapshot-session"
    created = api_harness.client.post(
        "/api/v1/sessions",
        json={"session_id": session_id, "is_returning_user": True},
    )
    assert created.status_code == 201, created.text
    event = event_payload(
        EventType.ITEM_ADDED_TO_CART,
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
    )
    response = api_harness.client.post("/api/v1/events", json=event)
    assert response.status_code == 202, response.text

    first = api_harness.client.get(f"/api/v1/sessions/{session_id}")
    api_harness.store.delete(f"session:{session_id}:state")
    second = api_harness.client.get(f"/api/v1/sessions/{session_id}")

    assert first.status_code == second.status_code == 200
    body = first.json()
    assert body["feature_schema_version"] == FEATURE_SCHEMA_VERSION
    assert tuple(body["current_features"]) == FEATURE_NAMES
    assert body["current_features"]["c_item_count"] == 1
    assert body["current_features"]["p_max_item_price"] == 71_999
    assert body["current_features"]["x_is_returning_user"] == 1
    assert second.json()["current_features"]["x_is_returning_user"] == 1

    with api_harness.sessions() as db:
        snapshots = list(db.scalars(
            select(SessionFeatureSnapshot)
            .where(SessionFeatureSnapshot.session_id == session_id)
            .order_by(SessionFeatureSnapshot.computed_at)
        ))
    assert len(snapshots) == 2
    assert all(item.feature_schema_version == FEATURE_SCHEMA_VERSION for item in snapshots)
    assert all(tuple(item.features) == FEATURE_NAMES for item in snapshots)
    assert all(item.trigger_event_id == event["event_id"] for item in snapshots)


def test_user_history_uses_smoothed_aggregates_and_cold_start_defaults(api_harness):
    observed_at = datetime(2026, 8, 2, 12, tzinfo=timezone.utc)
    user_id = "history-user"
    with api_harness.sessions.begin() as db:
        db.add(User(
            user_id=user_id,
            is_synthetic=True,
            lifetime_orders=0,
            avg_order_value=0,
            return_rate=0.1,
        ))
        db.flush()
        sessions = [
            ShoppingSession(
                session_id=f"history-session-{index}",
                user_id=user_id,
                started_at=observed_at - timedelta(days=index, seconds=duration),
                ended_at=observed_at - timedelta(days=index),
                outcome=outcome,
                outcome_resolved_at=observed_at - timedelta(days=index),
                is_synthetic=True,
            )
            for index, (outcome, duration) in enumerate(
                (("CONVERTED", 300), ("CONVERTED", 600), ("ABANDONED", 900)),
                start=1,
            )
        ]
        db.add_all(sessions)
        db.flush()
        db.add_all([
            Order(
                order_id="history-order-1",
                session_id=sessions[0].session_id,
                user_id=user_id,
                placed_at=observed_at - timedelta(days=1),
                order_value=100,
                discount_applied=10,
                payment_method="CARD",
                items=[{"category": "mobiles", "quantity": 1}],
            ),
            Order(
                order_id="history-order-2",
                session_id=sessions[1].session_id,
                user_id=user_id,
                placed_at=observed_at - timedelta(days=2),
                order_value=300,
                discount_applied=0,
                payment_method="UPI",
                items=[{"category": "appliances", "quantity": 2}],
            ),
        ])

    with api_harness.sessions() as db:
        history = user_history(db, user_id, as_of=observed_at)
        anonymous = user_history(db, "missing-user", as_of=observed_at)
        snapshot_count = db.scalar(select(func.count()).select_from(SessionFeatureSnapshot))

    assert history.lifetime_orders == 2
    assert history.prior_abandonment_rate == 0.4
    assert history.avg_order_value == 200
    assert history.discount_usage_rate == 0.5
    assert history.category_order_counts == {"appliances": 2, "mobiles": 1}
    assert history.avg_session_to_purchase_s == 450
    assert history.days_since_last_purchase == 1
    assert history.return_rate == 0.1
    assert history.payment_method_on_file is True
    assert history.affinity_informational == history.affinity_incentive == 0.5
    assert len(history.products) == 50

    assert anonymous.lifetime_orders == 0
    assert anonymous.prior_abandonment_rate == 0.5
    assert anonymous.avg_order_value == 15_000
    assert anonymous.discount_usage_rate == 0.3
    assert snapshot_count == 0
