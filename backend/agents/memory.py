"""Per-session memory for the intervention engine.

Tracks which levers have already been shown this session and how the shopper
responded, so the Ranking Agent can penalise repeating something just
dismissed, and so the log doubles as the (state, action, reward) trail a future
RL policy would train on — nothing is trained yet, but the schema is written
now so collection starts from day one.

Process-local in-memory, same caveat as `agents.gate.GateStore`: fine for a
single-instance demo, would move to Redis to survive restarts / be shared
across replicas in production.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

FeedbackAction = Literal["shown", "accepted", "dismissed", "converted"]


@dataclass
class FeedbackEvent:
    lever_id: str
    action: FeedbackAction
    at: float


@dataclass
class SessionMemory:
    events: List[FeedbackEvent] = field(default_factory=list)

    def record(self, lever_id: str, action: FeedbackAction, at: Optional[float] = None) -> None:
        self.events.append(FeedbackEvent(lever_id, action, at if at is not None else time.time()))

    def was_dismissed(self, lever_id: str) -> bool:
        return any(e.lever_id == lever_id and e.action == "dismissed" for e in self.events)

    def shown_count(self, lever_id: str) -> int:
        return sum(1 for e in self.events if e.lever_id == lever_id and e.action == "shown")


class InterventionMemoryStore:
    """In-memory session store. Mirrors `agents.gate.GateStore`."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionMemory] = {}

    def get(self, session_id: str) -> SessionMemory:
        return self._sessions.setdefault(session_id, SessionMemory())

    def record(
        self, session_id: str, lever_id: str, action: FeedbackAction, at: Optional[float] = None
    ) -> None:
        self.get(session_id).record(lever_id, action, at)

    def reset(self, session_id: Optional[str] = None) -> None:
        if session_id is None:
            self._sessions.clear()
        else:
            self._sessions.pop(session_id, None)


# Module-level store used by the API.
memory_store = InterventionMemoryStore()
