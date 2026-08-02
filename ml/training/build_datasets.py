from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from backend.domain.events import EventEnvelope
from backend.feature_engine.compute import compute_features
from backend.feature_engine.schema import (
    FEATURE_NAMES,
    RISK_MODEL_FEATURES,
    UserHistory,
)
from backend.session_state.state import SessionState
from backend.session_state.updater import apply
from ml.simulator.catalog import load_catalog, product_facts_by_id


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DECISION_EVENT_TYPES = {"CART_VIEWED", "CHECKOUT_STARTED", "PAYMENT_FAILED"}
IDENTIFIER_COLUMNS = (
    "decision_point_id",
    "session_id",
    "user_id",
    "split",
    "sequence_no",
    "client_timestamp",
)
LABEL_COLUMNS = ("y_abandoned", "y_causes")


def _write_parquet(frame: pd.DataFrame, path: Path) -> None:
    frame.to_parquet(
        path,
        engine="pyarrow",
        index=False,
        compression="zstd",
        use_dictionary=False,
    )


def _split_users(user_ids: Iterable[str]) -> dict[str, str]:
    users = pd.DataFrame({"user_id": sorted(set(user_ids))})
    first = GroupShuffleSplit(n_splits=1, train_size=0.70, random_state=42)
    train_indices, holdout_indices = next(first.split(users, groups=users["user_id"]))
    holdout = users.iloc[holdout_indices].reset_index(drop=True)
    second = GroupShuffleSplit(n_splits=1, train_size=0.50, random_state=43)
    val_relative, test_relative = next(
        second.split(holdout, groups=holdout["user_id"])
    )
    assignments = {
        user_id: "train" for user_id in users.iloc[train_indices]["user_id"]
    }
    assignments.update({
        user_id: "val" for user_id in holdout.iloc[val_relative]["user_id"]
    })
    assignments.update({
        user_id: "test" for user_id in holdout.iloc[test_relative]["user_id"]
    })
    split_sets = {
        split: {user_id for user_id, assigned in assignments.items() if assigned == split}
        for split in ("train", "val", "test")
    }
    assert not (split_sets["train"] & split_sets["val"])
    assert not (split_sets["train"] & split_sets["test"])
    assert not (split_sets["val"] & split_sets["test"])
    assert len(assignments) == len(users)
    return assignments


def _history_from_user(
    row: Any,
    products: dict[str, Any],
) -> UserHistory:
    return UserHistory(
        lifetime_orders=int(row.lifetime_orders),
        prior_abandonment_rate=float(row.prior_abandonment_rate),
        avg_order_value=float(row.avg_order_value),
        discount_usage_rate=float(row.discount_usage_rate),
        category_order_counts=json.loads(row.category_order_counts_json),
        days_since_last_purchase=float(row.days_since_last_purchase),
        avg_session_to_purchase_s=float(row.avg_session_to_purchase_s),
        return_rate=float(row.return_rate),
        affinity_informational=float(row.affinity_informational),
        affinity_incentive=float(row.affinity_incentive),
        payment_method_on_file=bool(row.payment_method_on_file),
        products=products,
    )


def event_envelope(row: Any) -> EventEnvelope:
    return EventEnvelope.model_validate({
        "event_id": row.event_id,
        "event_type": row.event_type,
        "session_id": row.session_id,
        "user_id": row.user_id,
        "product_id": row.product_id if pd.notna(row.product_id) else None,
        "sequence_no": int(row.sequence_no),
        "client_timestamp": row.client_timestamp,
        "metadata": json.loads(row.metadata_json),
    })


def _compact_recent_events(state: SessionState, next_sequence_no: int) -> None:
    """Keep the exact feature-relevant projection of serving's 50-event window.

    ``compute_features`` reads recent events only for delivery observations and
    the maximum sequence number. The serving updater deep-copies its immutable
    state on every transition; retaining unrelated payloads during a 680k-event
    offline replay adds quadratic copying work without changing one feature.
    This projection preserves both values while every event still passes through
    ``session_state.updater.apply``.
    """

    if not state.recent_events:
        return
    minimum_sequence = max(1, next_sequence_no - 49)
    latest = max(
        state.recent_events,
        key=lambda item: int(item.get("sequence_no", 0)),
    )
    retained = [
        item
        for item in state.recent_events
        if item.get("event_type") == "DELIVERY_CHECKED"
        and int(item.get("sequence_no", 0)) >= minimum_sequence
    ]
    if latest not in retained:
        retained.append(latest)
    retained.sort(key=lambda item: int(item.get("sequence_no", 0)))
    state.recent_events = retained


def replay_feature_rows(
    events: pd.DataFrame,
    history: UserHistory,
    *,
    is_returning_user: bool,
) -> list[dict[str, Any]]:
    """Replay through the serving updater and canonical feature function."""

    first = events.iloc[0]
    state = SessionState(
        session_id=str(first.session_id),
        is_returning_user=is_returning_user,
    )
    rows: list[dict[str, Any]] = []
    for raw in events.itertuples(index=False):
        event = event_envelope(raw)
        pre_end = event.event_type.value == "SESSION_ENDED"
        should_sample = event.event_type.value in DECISION_EVENT_TYPES or pre_end
        if pre_end and should_sample:
            point_history = replace(history, as_of=event.client_timestamp)
            rows.append({
                "sequence_no": event.sequence_no - 1,
                "client_timestamp": event.client_timestamp.isoformat(),
                **compute_features(state, point_history),
            })
        if not pre_end:
            _compact_recent_events(state, event.sequence_no)
        state = apply(state, event, server_timestamp=event.client_timestamp)
        if should_sample and not pre_end:
            point_history = replace(history, as_of=event.client_timestamp)
            rows.append({
                "sequence_no": event.sequence_no,
                "client_timestamp": event.client_timestamp.isoformat(),
                **compute_features(state, point_history),
            })
    return rows


def assert_no_leakage(feature_columns: Iterable[str]) -> None:
    columns = tuple(feature_columns)
    forbidden_exact = {"persona", "cause_strength", "cause_strengths"}
    assert not (forbidden_exact & set(columns)), "latent simulator state leaked"
    assert not any(column.startswith("y_") for column in columns), "label leaked"
    assert not any(
        column.startswith("i_") for column in RISK_MODEL_FEATURES
    ), "post-treatment feature entered the risk matrix"
    assert columns == FEATURE_NAMES, "feature matrix does not match serving schema"


def build_datasets(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    *,
    seed: int | None = None,
) -> pd.DataFrame:
    data_path = Path(data_dir)
    if seed is None:
        manifest_path = data_path / "dataset_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"{manifest_path} is missing; run ml.simulator.generate first"
            )
        seed = int(json.loads(manifest_path.read_text(encoding="utf-8"))["seed"])

    events = pd.read_parquet(data_path / "events.parquet")
    sessions = pd.read_parquet(data_path / "sessions.parquet")
    users = pd.read_parquet(data_path / "users.parquet")
    truth = pd.read_parquet(data_path / "ground_truth.parquet")
    products = product_facts_by_id(load_catalog(seed=seed))
    split_by_user = _split_users(users["user_id"])
    users_by_id = {row.user_id: row for row in users.itertuples(index=False)}
    session_labels = sessions.set_index("session_id")["outcome"].to_dict()
    causes_by_session = truth.set_index("session_id")["causes"].to_dict()

    rows: list[dict[str, Any]] = []
    grouped = events.sort_values(["session_id", "sequence_no"]).groupby(
        "session_id", sort=True
    )
    for session_id, session_events in grouped:
        user_id = str(session_events["user_id"].iat[0])
        user = users_by_id[user_id]
        history = _history_from_user(user, products)
        points = replay_feature_rows(
            session_events,
            history,
            is_returning_user=bool(user.is_returning_user),
        )
        causes = sorted(str(value) for value in causes_by_session[session_id])
        for point_index, point in enumerate(points, start=1):
            rows.append({
                "decision_point_id": f"{session_id}:dp-{point_index:02d}",
                "session_id": session_id,
                "user_id": user_id,
                "split": split_by_user[user_id],
                "sequence_no": point.pop("sequence_no"),
                "client_timestamp": point.pop("client_timestamp"),
                **point,
                "y_abandoned": int(session_labels[session_id] == "ABANDONED"),
                "y_causes": causes,
            })

    columns = [*IDENTIFIER_COLUMNS, *FEATURE_NAMES, *LABEL_COLUMNS]
    decision_points = pd.DataFrame(rows, columns=columns).sort_values(
        ["session_id", "sequence_no", "decision_point_id"]
    ).reset_index(drop=True)
    assert_no_leakage(FEATURE_NAMES)

    split_users = {
        split: set(
            decision_points.loc[decision_points["split"] == split, "user_id"]
        )
        for split in ("train", "val", "test")
    }
    assert not split_users["train"] & split_users["val"]
    assert not split_users["train"] & split_users["test"]
    assert not split_users["val"] & split_users["test"]

    _write_parquet(decision_points, data_path / "decision_points.parquet")
    return decision_points


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay simulator events through serving code into ML rows."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    frame = build_datasets(args.data_dir)
    print(f"wrote {len(frame):,} rows to {args.data_dir / 'decision_points.parquet'}")


if __name__ == "__main__":
    main()
