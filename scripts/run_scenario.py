from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = PROJECT_ROOT / "fixtures" / "scenarios"


def deterministic_uuid4(key: str) -> str:
    value = bytearray(__import__("hashlib").sha256(key.encode()).digest()[:16])
    value[6] = (value[6] & 0x0F) | 0x40
    value[8] = (value[8] & 0x3F) | 0x80
    return str(UUID(bytes=bytes(value)))


def load_fixture(letter: str) -> dict[str, Any]:
    path = SCENARIO_DIR / f"{letter.lower()}.json"
    if not path.exists():
        raise ValueError(f"Unknown scenario {letter!r}; expected A-H")
    return json.loads(path.read_text(encoding="utf-8"))


def _event_payload(
    scenario: str,
    session_id: str,
    sequence_no: int,
    spec: dict[str, Any],
    timestamp: datetime,
) -> dict[str, Any]:
    payload = {
        "event_id": deterministic_uuid4(f"{scenario}:{session_id}:{sequence_no}"),
        "event_type": spec["event_type"],
        "session_id": session_id,
        "sequence_no": sequence_no,
        "client_timestamp": timestamp.isoformat(),
        "metadata": spec.get("metadata", {}),
    }
    if spec.get("product_id"):
        payload["product_id"] = spec["product_id"]
    return payload


def _assert_expected(result: dict[str, Any], expected: dict[str, Any]) -> None:
    causes = result.get("root_causes", [])
    dominant_cause = causes[0].get("cause") if causes else None
    recommended = result.get("recommended_intervention") or {}
    actual = {
        "decision": result.get("decision"),
        "intervention": recommended.get("type"),
        "dominant_cause": dominant_cause,
        "experiment_group": result.get("experiment_group"),
    }
    mismatches = {
        key: {"expected": value, "actual": actual.get(key)}
        for key, value in expected.items()
        if actual.get(key) != value
    }
    if mismatches:
        raise AssertionError(json.dumps(mismatches, indent=2, ensure_ascii=False))


def run_fixture(client: TestClient, fixture: dict[str, Any]) -> list[dict[str, Any]]:
    from backend import config
    from backend.storage.db import SessionLocal
    from backend.storage.models import User

    # The interactive API debounces for three seconds. Fixture replay is an
    # explicit deterministic command, so it does not sleep between event replay
    # and the requested decision.
    config.DECISION_DEBOUNCE_SECONDS = 0
    results: list[dict[str, Any]] = []
    base_time = datetime.now(timezone.utc)
    scenario = fixture["scenario"]
    for session_index, session in enumerate(fixture["sessions"]):
        session_id = session["session_id"]
        user = session.get("user")
        if isinstance(user, dict):
            with SessionLocal.begin() as db:
                if db.get(User, user["user_id"]) is None:
                    db.add(User(
                        user_id=user["user_id"],
                        is_synthetic=True,
                        persona=user.get("persona"),
                        device_preference=user.get("device_preference", "MOBILE"),
                        lifetime_orders=int(user.get("lifetime_orders", 0)),
                        avg_order_value=float(user.get("avg_order_value", 15_000)),
                        prior_abandonment_rate=float(user.get("prior_abandonment_rate", 0.5)),
                        discount_usage_rate=float(user.get("discount_usage_rate", 0.3)),
                        return_rate=float(user.get("return_rate", 0.08)),
                        intervention_affinity={},
                    ))
        sequence_no = 0
        last_decision: dict[str, Any] | None = None
        for action_index, action in enumerate(session["actions"]):
            if "events" in action:
                for event in action["events"]:
                    for _ in range(int(event.get("repeat", 1))):
                        sequence_no += 1
                        event_timestamp = (
                            base_time - timedelta(
                                seconds=float(session.get("session_age_seconds", 180))
                            )
                            if event["event_type"] == "SESSION_STARTED"
                            else base_time
                        )
                        payload = _event_payload(
                            scenario,
                            session_id,
                            sequence_no,
                            event,
                            event_timestamp,
                        )
                        if isinstance(user, dict):
                            payload["user_id"] = user["user_id"]
                        response = client.post("/api/v1/events", json=payload)
                        if response.status_code != 202:
                            raise AssertionError(
                                f"{scenario}/{session_id} event {sequence_no} failed: "
                                f"{response.status_code} {response.text}"
                            )
            if "decide" in action:
                response = client.post(
                    f"/api/v1/sessions/{session_id}/decisions",
                    json={"trigger": action["decide"], "force": True},
                )
                if response.status_code != 200:
                    raise AssertionError(
                        f"{scenario}/{session_id} decision failed: "
                        f"{response.status_code} {response.text}"
                    )
                last_decision = response.json()
                if action.get("expect"):
                    _assert_expected(last_decision, action["expect"])
                results.append(last_decision)
            if action.get("dismiss_last"):
                if last_decision is None:
                    raise AssertionError("dismiss_last requires a preceding decision")
                intervention = last_decision["recommended_intervention"]["type"]
                for event_type, metadata in (
                    (
                        "INTERVENTION_SHOWN",
                        {
                            "decision_id": last_decision["decision_id"],
                            "intervention_id": intervention,
                            "surface": "INLINE_CARD",
                        },
                    ),
                    (
                        "INTERVENTION_DISMISSED",
                        {
                            "decision_id": last_decision["decision_id"],
                            "intervention_id": intervention,
                        },
                    ),
                ):
                    sequence_no += 1
                    payload = _event_payload(
                        scenario,
                        session_id,
                        sequence_no,
                        {"event_type": event_type, "metadata": metadata},
                        base_time + timedelta(seconds=session_index * 1_000 + sequence_no),
                    )
                    response = client.post("/api/v1/events", json=payload)
                    if response.status_code != 202:
                        raise AssertionError(response.text)
        if session.get("expect"):
            if last_decision is None:
                raise AssertionError(f"{session_id} did not produce a decision")
            _assert_expected(last_decision, session["expect"])
    return results


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Replay a deterministic demo scenario")
    parser.add_argument("scenario", choices=list("ABCDEFGH"), type=str.upper)
    args = parser.parse_args()

    from backend.main import app

    fixture = load_fixture(args.scenario)
    with TestClient(app) as client:
        results = run_fixture(client, fixture)
    print(json.dumps({
        "scenario": fixture["scenario"],
        "title": fixture["title"],
        "decisions": results,
    }, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
