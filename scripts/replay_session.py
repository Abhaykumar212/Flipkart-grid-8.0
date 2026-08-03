from __future__ import annotations

import argparse
import json

from sqlalchemy import select

from backend.orchestrator.pipeline import run_decision
from backend.storage.db import SessionLocal
from backend.storage.models import DecisionTrace
from backend.storage.session_store import InMemorySessionStore


def replay(session_id: str) -> dict[str, object]:
    store = InMemorySessionStore()
    with SessionLocal() as db:
        original = db.scalar(
            select(DecisionTrace)
            .where(DecisionTrace.session_id == session_id)
            .order_by(DecisionTrace.decision_time.desc())
            .limit(1)
        )
        if original is None:
            raise SystemExit(f"No decision trace found for session {session_id}")
        run = run_decision(
            session_id,
            original.trigger,
            db,
            store,
            force=True,
            now=original.decision_time,
        )
        replayed = run.response
        selected = replayed.get("recommended_intervention")
        selected_type = selected.get("type") if isinstance(selected, dict) else None
        original_score = next(
            (
                item.get("score")
                for item in original.utility_scores
                if item.get("intervention") == original.selected_intervention
            ),
            None,
        )
        replay_score = next(
            (
                item.get("score")
                for item in replayed.get("utility_scores", [])
                if item.get("intervention") == selected_type
            ),
            None,
        )
        return {
            "session_id": session_id,
            "original_decision_id": original.decision_id,
            "original_intervention": original.selected_intervention,
            "replayed_intervention": selected_type,
            "original_score": original_score,
            "replayed_score": replay_score,
            "matches": (
                original.selected_intervention == selected_type
                and original_score == replay_score
            ),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()
    print(json.dumps(replay(args.session_id), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
