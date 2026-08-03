"""Per-session memory for the intervention engine.

Tracks which levers have already been shown this session and how the shopper
responded, so the Ranking Agent can penalise repeating something just
dismissed, and so the log doubles as the (state, action, reward) trail a future
RL policy would train on — nothing is trained yet, but the schema is written
now so collection starts from day one.

Backed by the `intervention_events` table (see `backend/db.py`), which is also
the source of truth for the session ledger. Two things share the name "shown":
the top-3 levers the Ranking Agent scored, and the single lever the client
actually rendered. The `source` column separates them, and `get` reads back only
ranking exposure plus shopper responses, so the repetition penalty sees exactly
the event stream it saw before the migration.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from .. import db

FeedbackAction = Literal["shown", "accepted", "dismissed", "converted"]

# Ranking-time exposure vs. a shopper's response to something rendered. Only
# `shown` comes from `build_intervention_plan`; the rest arrive from
# `/api/intervention-feedback` after a lever was actually delivered.
_RANKED_ACTIONS = ("shown",)


@dataclass
class FeedbackEvent:
    lever_id: str
    action: FeedbackAction
    at: float


@dataclass
class SessionMemory:
    """Detached read snapshot of one session's events.

    Since the move to SQLite, `record` here mutates the snapshot only —
    `InterventionMemoryStore.record` is the write path.
    """

    events: List[FeedbackEvent] = field(default_factory=list)

    def record(self, lever_id: str, action: FeedbackAction, at: Optional[float] = None) -> None:
        self.events.append(FeedbackEvent(lever_id, action, at if at is not None else time.time()))

    def was_dismissed(self, lever_id: str) -> bool:
        return any(e.lever_id == lever_id and e.action == "dismissed" for e in self.events)

    def shown_count(self, lever_id: str) -> int:
        return sum(1 for e in self.events if e.lever_id == lever_id and e.action == "shown")


class InterventionMemoryStore:
    """SQLite-backed session store. Mirrors `agents.gate.GateStore`."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path
        self._owned: Optional[sqlite3.Connection] = None

    @property
    def _db(self) -> sqlite3.Connection:
        if self._db_path is None:
            return db.get_db()
        if self._owned is None:
            self._owned = db.get_db(self._db_path)
        return self._owned

    def get(self, session_id: str) -> SessionMemory:
        # Ranking exposure plus shopper responses — exactly the event stream this
        # store held before the migration. Deliberately excludes the delivery
        # layer's own `shown` rows (source='delivered'): those record that a lever
        # rendered, and counting them here would inflate `shown_count` and change
        # the repetition penalty.
        rows = self._db.execute(
            "SELECT lever_id, action, created_at FROM intervention_events "
            "WHERE session_id = ? "
            "  AND (source = 'ranked' OR action IN ('accepted', 'dismissed', 'converted')) "
            "ORDER BY id",
            (session_id,),
        ).fetchall()
        return SessionMemory(
            events=[
                FeedbackEvent(row["lever_id"], row["action"], row["created_at"]) for row in rows
            ]
        )

    def record(
        self, session_id: str, lever_id: str, action: FeedbackAction, at: Optional[float] = None
    ) -> None:
        at = at if at is not None else time.time()
        source = "ranked" if action in _RANKED_ACTIONS else "delivered"
        connection = self._db
        with connection:
            db.touch_session(connection, session_id, at)
            connection.execute(
                "INSERT INTO intervention_events "
                "(session_id, lever_id, action, source, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, lever_id, action, source, at),
            )

    def reset(self, session_id: Optional[str] = None) -> None:
        connection = self._db
        with connection:
            if session_id is None:
                connection.execute("DELETE FROM intervention_events")
            else:
                connection.execute(
                    "DELETE FROM intervention_events WHERE session_id = ?", (session_id,)
                )


# Module-level store used by the API.
memory_store = InterventionMemoryStore()
