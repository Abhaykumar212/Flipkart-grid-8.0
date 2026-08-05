"""SQLite persistence for session-scoped agent state.

Replaces the process-local dicts in `agents/gate.py` and `agents/memory.py`, so a
backend restart no longer resets RCA cooldowns, the per-session analysis cap, or
the intervention history that `score_candidate`'s repetition penalty reads.

Stdlib `sqlite3` only — no ORM, no extra dependency. The whole persistence layer
is five tables and a connection helper, and at this size an abstraction would
cost more than it saves.

Threading: FastAPI runs `def` endpoints in an anyio worker threadpool, so the
shared app connection is held in a `threading.local()`. A single connection
shared across threads would need `check_same_thread=False` plus a lock; a
connection per thread is simpler and is exactly what WAL mode is designed for
(concurrent readers alongside one writer).
"""

from __future__ import annotations

import sqlite3
import threading
from typing import Optional

from . import config

DB_DIR = config.PROJECT_ROOT / "backend" / "data"
DB_PATH = DB_DIR / "app.db"

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    created_at   REAL NOT NULL,
    last_seen_at REAL NOT NULL
);

-- One row per session. Mirrors `agents.gate.SessionState` field for field:
-- fire_count <-> analyses_run, root_cause_signature <-> last_signature,
-- last_fired_at <-> last_run_at.
CREATE TABLE IF NOT EXISTS gate_state (
    session_id            TEXT PRIMARY KEY,
    root_cause_signature  TEXT,
    last_fired_at         REAL NOT NULL DEFAULT 0,
    fire_count            INTEGER NOT NULL DEFAULT 0
);

-- Append-only. `source` separates two things that both used to be called
-- "shown": 'ranked' rows are the top-3 the Ranking Agent scored (what the
-- repetition penalty reads), 'delivered' rows are the single lever the client
-- actually rendered (what the ledger counts), and 'suppressed' rows are rung-3
-- levers considered and then withheld by policy.
CREATE TABLE IF NOT EXISTS intervention_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT NOT NULL,
    lever_id       TEXT NOT NULL,
    intensity_rung INTEGER,
    surface        TEXT,
    root_cause     TEXT,
    confidence     TEXT,
    reason         TEXT,
    action         TEXT NOT NULL CHECK (
        action IN ('shown', 'accepted', 'dismissed', 'converted', 'ignored', 'suppressed')
    ),
    source         TEXT NOT NULL DEFAULT 'ranked' CHECK (
        source IN ('ranked', 'delivered', 'suppressed')
    ),
    -- Set only on the 'ranked'/'shown' row the approved lever already had (see
    -- agents/explanation_scorer.py): 'grounded' when the justification text
    -- passed the grounding check untouched, 'regenerated' when a flagged claim
    -- was rewritten and passed a deterministic re-check, 'template_fallback'
    -- when even the rewrite didn't hold up and the explanation was replaced
    -- with a plain evidence listing. NULL for every row this agent never
    -- touched.
    explanation_verdict TEXT,
    created_at     REAL NOT NULL
);

-- The delivery layer's verdict for one pipeline run. "Do nothing" is recorded
-- exactly like "intervene" — an absence of a row would be indistinguishable
-- from a run that never happened.
CREATE TABLE IF NOT EXISTS decisions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL,
    decision_type TEXT NOT NULL CHECK (decision_type IN ('intervene', 'do_nothing', 'elicited')),
    reason        TEXT,
    detail        TEXT,
    root_cause    TEXT,
    probability   REAL,
    created_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS reservations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    quantity    INTEGER NOT NULL,
    reserved_at REAL NOT NULL,
    expires_at  REAL NOT NULL,
    released_at REAL
);

CREATE INDEX IF NOT EXISTS idx_events_session ON intervention_events (session_id);
CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions (session_id);
CREATE INDEX IF NOT EXISTS idx_reservations_session ON reservations (session_id);
CREATE INDEX IF NOT EXISTS idx_reservations_product ON reservations (product_id);
CREATE TABLE IF NOT EXISTS session_emails (
    session_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    captured_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS session_timelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_data TEXT NOT NULL,
    timestamp REAL NOT NULL,
    duration_seconds REAL,
    page TEXT
);

CREATE TABLE IF NOT EXISTS reengagement_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    email_to TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_html TEXT NOT NULL,
    analysis_summary TEXT,
    behavioral_signals TEXT,
    generated_at REAL NOT NULL,
    sent_at REAL,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_timeline_session ON session_timelines (session_id);
CREATE INDEX IF NOT EXISTS idx_reengagement_session ON reengagement_emails (session_id);

-- Mock account system: no passwords, no real auth — a demo user is just an
-- email the shopper typed into the "Sign in" modal. `id` is derived from the
-- email (see `backend/accounts.py`) so logging in twice with the same address
-- always resolves to the same row instead of minting duplicates.
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    email      TEXT NOT NULL UNIQUE,
    name       TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);

-- One row per placed order. `items_json`/`address_json` are stored as opaque
-- JSON rather than normalized lines — the catalog itself lives on the
-- frontend (see `ProductAvailability`'s docstring), so there is no products
-- table here to foreign-key against, and an order is a receipt, not a query
-- surface that needs line-level joins.
CREATE TABLE IF NOT EXISTS orders (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    user_id         TEXT,
    items_json      TEXT NOT NULL,
    address_json    TEXT NOT NULL,
    payment_method  TEXT NOT NULL,
    total_inr       REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'placed',
    created_at      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON orders (user_id);
CREATE INDEX IF NOT EXISTS idx_orders_session ON orders (session_id);

-- Admin-authored catalog additions. Deliberately separate from (not a
-- migration of) `src/data/products.ts` — that file stays the hand-authored
-- source of truth for the 50-product demo catalog; this table is the "real
-- backend" a catalog admin would actually write to. The frontend merges rows
-- from here into the storefront at read time (see `AdminCatalogContext`).
CREATE TABLE IF NOT EXISTS admin_products (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    brand           TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT 'electronics',
    mrp             REAL NOT NULL,
    selling_price   REAL NOT NULL,
    image_url       TEXT NOT NULL DEFAULT '',
    stock_qty       INTEGER NOT NULL DEFAULT 0,
    description     TEXT NOT NULL DEFAULT '',
    created_at      REAL NOT NULL,
    updated_at      REAL NOT NULL
);
"""

# Columns added after the initial release of a table that already shipped
# without them. `ALTER TABLE ... ADD COLUMN` has no `IF NOT EXISTS` in
# SQLite, so each entry is applied with its own "does this column exist yet"
# guard in `_apply_migrations` instead of unconditionally (which would raise
# `duplicate column name` on every second boot).
_MIGRATIONS = [
    ("sessions", "user_id", "TEXT"),
    # Deterministic per-session A/B bucket ('a' / 'b'), assigned once and
    # reused for the life of the session — see `backend/ab_testing.py`.
    ("sessions", "ab_variant", "TEXT"),
    ("decisions", "ab_variant", "TEXT"),
]


def _apply_migrations(connection: sqlite3.Connection) -> None:
    for table, column, coltype in _MIGRATIONS:
        existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_schema(connection: sqlite3.Connection) -> None:
    """Create every table and index if absent. Idempotent, safe to re-run."""
    with connection:
        connection.executescript(SCHEMA)
        _apply_migrations(connection)


def _connect(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    # WAL lets the ledger endpoint read while a decision is being written.
    # It is a no-op on ':memory:', which sqlite keeps in journal mode.
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    init_schema(connection)
    return connection


def get_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Connection to the app database, or to `db_path` if given.

    `db_path=None` returns the shared app connection for the calling thread,
    creating `backend/data/` on first use. Passing an explicit path (tests use
    `":memory:"`) returns a fresh dedicated connection the caller owns — that is
    the seam that keeps unit tests isolated from each other and from the real db.
    """
    if db_path is not None:
        return _connect(db_path)

    connection = getattr(_local, "connection", None)
    if connection is None:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        connection = _connect(str(DB_PATH))
        _local.connection = connection
    return connection


def touch_session(connection: sqlite3.Connection, session_id: str, at: float) -> None:
    """Record that this session exists and was just active.

    Called from every write path, so `sessions` stays a complete list of the
    sessions the other tables reference without needing a foreign key that would
    force an ordering constraint on the writes.
    """
    connection.execute(
        """
        INSERT INTO sessions (session_id, created_at, last_seen_at)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
        """,
        (session_id, at, at),
    )


def reset_thread_connection() -> None:
    """Drop this thread's cached connection. Tests only."""
    connection = getattr(_local, "connection", None)
    if connection is not None:
        connection.close()
        _local.connection = None


__all__ = [
    "DB_PATH",
    "get_db",
    "init_schema",
    "touch_session",
    "reset_thread_connection",
]
