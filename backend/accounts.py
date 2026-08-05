"""Mock account system — email-only "sign in", no password, no session tokens.

This is a hackathon demo, not an auth service: `login()` upserts a `users` row
keyed by a stable id derived from the email address, and the frontend just
remembers that id in localStorage. There is no credential to check, so there is
nothing to verify — the point of this module is giving a shopper's session
history somewhere durable to attach to, not access control.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from typing import Any, Dict, List, Optional

from . import db


def _user_id(email: str) -> str:
    """Stable id for an email address, so logging in twice never duplicates."""
    digest = hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]
    return f"usr_{digest}"


def login(connection: sqlite3.Connection, email: str, name: str) -> Dict[str, Any]:
    """Find-or-create the user for this email. Returns the user row as a dict."""
    email = email.strip().lower()
    user_id = _user_id(email)
    now = time.time()
    with connection:
        connection.execute(
            """
            INSERT INTO users (id, email, name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                name = CASE WHEN excluded.name != '' THEN excluded.name ELSE users.name END
            """,
            (user_id, email, name.strip(), now),
        )
    row = connection.execute("SELECT id, email, name, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row)


def link_session(connection: sqlite3.Connection, session_id: str, user_id: str) -> None:
    """Attach a browser session to a logged-in user, so its history rolls up."""
    now = time.time()
    with connection:
        db.touch_session(connection, session_id, now)
        connection.execute("UPDATE sessions SET user_id = ? WHERE session_id = ?", (user_id, session_id))


def _session_summaries(connection: sqlite3.Connection, session_ids: List[str]) -> List[Dict[str, Any]]:
    if not session_ids:
        return []
    placeholders = ",".join("?" for _ in session_ids)
    rows = connection.execute(
        f"""
        SELECT session_id, created_at, last_seen_at
        FROM sessions WHERE session_id IN ({placeholders})
        ORDER BY last_seen_at DESC
        """,
        session_ids,
    ).fetchall()
    summaries = []
    for row in rows:
        decision_counts = connection.execute(
            "SELECT decision_type, COUNT(*) AS n FROM decisions WHERE session_id = ? GROUP BY decision_type",
            (row["session_id"],),
        ).fetchall()
        counts = {d["decision_type"]: d["n"] for d in decision_counts}
        summaries.append(
            {
                "session_id": row["session_id"],
                "started_at": row["created_at"],
                "last_seen_at": row["last_seen_at"],
                "interventions_shown": counts.get("intervene", 0),
                "held": counts.get("do_nothing", 0),
            }
        )
    return summaries


def get_history(connection: sqlite3.Connection, user_id: str) -> Dict[str, Any]:
    """Everything the account page shows: profile, past orders, session history."""
    user_row = connection.execute("SELECT id, email, name, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    if user_row is None:
        return {"user": None, "orders": [], "sessions": []}

    order_rows = connection.execute(
        """
        SELECT id, session_id, items_json, address_json, payment_method, total_inr, status, created_at
        FROM orders WHERE user_id = ? ORDER BY created_at DESC
        """,
        (user_id,),
    ).fetchall()
    import json as _json

    orders = [
        {
            "id": row["id"],
            "session_id": row["session_id"],
            "items": _json.loads(row["items_json"]),
            "address": _json.loads(row["address_json"]),
            "payment_method": row["payment_method"],
            "total_inr": row["total_inr"],
            "status": row["status"],
            "created_at": row["created_at"],
        }
        for row in order_rows
    ]

    session_rows = connection.execute(
        "SELECT session_id FROM sessions WHERE user_id = ?", (user_id,)
    ).fetchall()
    sessions = _session_summaries(connection, [row["session_id"] for row in session_rows])

    return {"user": dict(user_row), "orders": orders, "sessions": sessions}


__all__ = ["login", "link_session", "get_history"]
