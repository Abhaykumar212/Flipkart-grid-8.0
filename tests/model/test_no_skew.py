from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import json

import numpy as np
import pandas as pd

from backend.domain.events import EventEnvelope, EventType
from backend.feature_engine.compute import compute_features
from backend.feature_engine.schema import FEATURE_NAMES, ProductFacts, UserHistory
from backend.session_state.state import SessionState
from backend.session_state.updater import apply
from ml.training.build_datasets import replay_feature_rows
from tests.event_factories import DEFAULT_TIMESTAMP, event_payload


def _event_row(event_type: EventType, sequence_no: int) -> dict:
    payload = event_payload(
        event_type,
        session_id="no-skew-session",
        sequence_no=sequence_no,
        timestamp=DEFAULT_TIMESTAMP + timedelta(seconds=sequence_no * 5),
    )
    return {
        **{key: value for key, value in payload.items() if key != "metadata"},
        "user_id": "no-skew-user",
        "product_id": payload.get("product_id"),
        "client_timestamp": payload["client_timestamp"],
        "metadata_json": json.dumps(payload["metadata"], sort_keys=True),
    }


def test_simulator_replay_and_serving_path_features_are_byte_identical():
    event_types = (
        EventType.SESSION_STARTED,
        EventType.PRODUCT_VIEWED,
        EventType.REVIEW_OPENED,
        EventType.REVIEW_DWELL_RECORDED,
        EventType.ITEM_ADDED_TO_CART,
        EventType.CART_VIEWED,
    )
    events = pd.DataFrame([
        _event_row(event_type, index)
        for index, event_type in enumerate(event_types, start=1)
    ])
    product = ProductFacts(
        product_id="p-1001",
        category="mobiles",
        mrp=79_900,
        selling_price=71_999,
        rating=4.6,
        rating_count=124_512,
        in_stock=True,
        quantity_left=18,
        estimated_delivery_days=1,
        emi_eligible=True,
        price_history=(76_999, 74_499, 71_999),
    )
    history = UserHistory(
        lifetime_orders=2,
        products={product.product_id: product},
    )

    simulator_features = replay_feature_rows(
        events, history, is_returning_user=True
    )[-1]
    state = SessionState(session_id="no-skew-session", is_returning_user=True)
    last_event = None
    for row in events.itertuples(index=False):
        last_event = EventEnvelope.model_validate({
            "event_id": row.event_id,
            "event_type": row.event_type,
            "session_id": row.session_id,
            "user_id": row.user_id,
            "product_id": row.product_id if pd.notna(row.product_id) else None,
            "sequence_no": row.sequence_no,
            "client_timestamp": row.client_timestamp,
            "metadata": json.loads(row.metadata_json),
        })
        state = apply(state, last_event, server_timestamp=last_event.client_timestamp)
    assert last_event is not None
    serving_features = compute_features(
        state, replace(history, as_of=last_event.client_timestamp)
    )

    simulator_vector = np.asarray(
        [simulator_features[name] for name in FEATURE_NAMES], dtype=np.float64
    )
    serving_vector = np.asarray(
        [serving_features[name] for name in FEATURE_NAMES], dtype=np.float64
    )
    assert simulator_vector.tobytes() == serving_vector.tobytes()


def test_compacted_replay_preserves_serving_fifty_event_delivery_window():
    event_types = [EventType.SESSION_STARTED, EventType.DELIVERY_CHECKED]
    event_types.extend([EventType.PRODUCT_VIEWED] * 56)
    event_types.extend([EventType.ITEM_ADDED_TO_CART, EventType.CART_VIEWED])
    events = pd.DataFrame([
        _event_row(event_type, index)
        for index, event_type in enumerate(event_types, start=1)
    ])
    product = ProductFacts(
        product_id="p-1001",
        category="mobiles",
        mrp=79_900,
        selling_price=71_999,
        rating=4.6,
        rating_count=124_512,
        in_stock=True,
        quantity_left=18,
        estimated_delivery_days=1,
        emi_eligible=True,
    )
    history = UserHistory(products={product.product_id: product})

    replayed = replay_feature_rows(events, history, is_returning_user=False)[-1]
    state = SessionState(session_id="no-skew-session")
    last_event = None
    for row in events.itertuples(index=False):
        last_event = EventEnvelope.model_validate({
            "event_id": row.event_id,
            "event_type": row.event_type,
            "session_id": row.session_id,
            "user_id": row.user_id,
            "product_id": row.product_id if pd.notna(row.product_id) else None,
            "sequence_no": row.sequence_no,
            "client_timestamp": row.client_timestamp,
            "metadata": json.loads(row.metadata_json),
        })
        state = apply(state, last_event, server_timestamp=last_event.client_timestamp)
    assert last_event is not None
    served = compute_features(
        state, replace(history, as_of=last_event.client_timestamp)
    )

    assert replayed["d_check_count"] == served["d_check_count"] == 1
    assert replayed["d_max_days"] == served["d_max_days"] == 1
    assert np.asarray(
        [replayed[name] for name in FEATURE_NAMES], dtype=np.float64
    ).tobytes() == np.asarray(
        [served[name] for name in FEATURE_NAMES], dtype=np.float64
    ).tobytes()
