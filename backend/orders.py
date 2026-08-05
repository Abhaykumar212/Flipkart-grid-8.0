"""Order placement — the real backend half of the checkout flow.

`src/routes/CheckoutPage.tsx` used to generate its own `OD…` id client-side and
never told the backend an order happened at all (see the now-resolved
`TODO(agent)` that used to sit there). This module is what that call now hits:
a real `orders` row, still explicitly a test-mode "payment" (no processor is
integrated — see `main.py`'s `/api/checkout` docstring) but a genuine
persisted receipt a shopper's account history can read back.
"""

from __future__ import annotations

import json
import random
import sqlite3
import time
from typing import Any, Dict, List, Optional

from . import db


def generate_order_id() -> str:
    """Same `OD<15 digits>` shape the old client-side generator used."""
    return "OD" + "".join(str(random.randint(0, 9)) for _ in range(15))


def place_order(
    connection: sqlite3.Connection,
    session_id: str,
    items: List[Dict[str, Any]],
    address: Dict[str, Any],
    payment_method: str,
    total_inr: float,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    order_id = generate_order_id()
    now = time.time()
    with connection:
        db.touch_session(connection, session_id, now)
        connection.execute(
            """
            INSERT INTO orders
                (id, session_id, user_id, items_json, address_json, payment_method, total_inr, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'placed', ?)
            """,
            (
                order_id,
                session_id,
                user_id,
                json.dumps(items),
                json.dumps(address),
                payment_method,
                total_inr,
                now,
            ),
        )
    return {"order_id": order_id, "status": "placed", "created_at": now}


__all__ = ["generate_order_id", "place_order"]
