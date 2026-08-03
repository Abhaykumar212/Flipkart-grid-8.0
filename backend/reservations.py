"""Inventory holds for hesitating shoppers.

When the pipeline diagnoses cost friction or product uncertainty on a high-risk
cart, one unit of the cart's most valuable line is held for ten minutes. Nothing
customer-facing announces it — the hold is what makes a scarcity signal honest
rather than decorative, not a message in itself.

Expiry is evaluated at read time (`active_count`), so there is no background
worker and no clock to keep running: a hold nobody reads costs nothing, and a
hold that lapsed is simply absent from the next count.

Writes to the `reservations` table from `backend/db.py`. Kept out of
`ledger.py`, which is about decisions the delivery layer made; this is about
stock.
"""

from __future__ import annotations

import sqlite3
import time
from typing import Optional

from . import db

HOLD_SECONDS = 600.0

# Only these two diagnoses justify a hold. Trust, checkout and delivery friction
# are about the *transaction*, not about whether the item is still there — a
# reservation would do nothing for them but consume stock.
RESERVING_CAUSES = frozenset({"product_uncertainty", "cost_friction"})


def reserve(
    connection: sqlite3.Connection,
    session_id: str,
    product_id: str,
    quantity: int = 1,
    at: Optional[float] = None,
) -> bool:
    """Hold `quantity` for this session. True if a new row was written.

    A session that already holds this product is a no-op rather than a second
    row: the gate allows up to 10 analyses per session, and stacking a hold per
    analysis would make one hesitating shopper read as ten units of demand.
    """
    at = at if at is not None else time.time()
    if _active_for_session(connection, session_id, product_id, at):
        return False

    with connection:
        db.touch_session(connection, session_id, at)
        connection.execute(
            """
            INSERT INTO reservations
                (product_id, session_id, quantity, reserved_at, expires_at, released_at)
            VALUES (?, ?, ?, ?, ?, NULL)
            """,
            (product_id, session_id, quantity, at, at + HOLD_SECONDS),
        )
    return True


def release(
    connection: sqlite3.Connection,
    session_id: str,
    product_id: str,
    at: Optional[float] = None,
) -> int:
    """Drop this session's holds on a product. Returns how many were released.

    Called when the shopper adds the product to their cart: the cart itself is
    now the claim on that unit, and a speculative hold on top of it would
    double-count the same shopper.
    """
    at = at if at is not None else time.time()
    with connection:
        cursor = connection.execute(
            "UPDATE reservations SET released_at = ? "
            "WHERE session_id = ? AND product_id = ? AND released_at IS NULL",
            (at, session_id, product_id),
        )
    return cursor.rowcount


def active_count(
    connection: sqlite3.Connection, product_id: str, now: Optional[float] = None
) -> int:
    """Units currently held: not released, not expired as of `now`."""
    now = now if now is not None else time.time()
    row = connection.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS held FROM reservations "
        "WHERE product_id = ? AND released_at IS NULL AND expires_at > ?",
        (product_id, now),
    ).fetchone()
    return int(row["held"])


def _active_for_session(
    connection: sqlite3.Connection, session_id: str, product_id: str, now: float
) -> bool:
    row = connection.execute(
        "SELECT 1 FROM reservations "
        "WHERE session_id = ? AND product_id = ? AND released_at IS NULL AND expires_at > ? "
        "LIMIT 1",
        (session_id, product_id, now),
    ).fetchone()
    return row is not None
