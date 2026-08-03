# CLAUDE.md

Single monorepo: FastAPI backend (`backend/`), XGBoost pipeline (`ml/`), React 18 +
TypeScript + Vite frontend (`src/`) all at repo root — the root `README.md` describes
a nested `Flipkart-grid-8.0/` layout that does not exist; ignore it. Full architecture
snapshot lives in [SYSTEM_AUDIT.md](SYSTEM_AUDIT.md) — read it before making
non-trivial changes, it's kept current on request.

## Running it

```bash
npm run dev                                          # frontend, :5173
python -m uvicorn backend.main:app --port 8000        # backend, :8000
```

Both are also registered in `.claude/launch.json` (`flipkart-dev`, `backend`) for the
preview tool. Model artifacts must exist under `ml/artifacts/` before the backend will
boot (`python ml/generate_dataset.py && python ml/train_model.py` if missing).

Tests: `python -m unittest discover -s tests -v` (no `npm test` script exists yet).

## The pipeline, in order

1. `sessionTracker` (`src/lib/tracker.ts`) builds a 22-feature vector client-side.
2. `POST /api/predict-abandonment` → XGBoost + SHAP (`backend/main.py`).
3. `POST /api/root-cause-analysis` re-runs inference server-side, then
   `agents/gate.py` decides whether to spend an LLM call, then (if fired)
   `agents/root_cause.py` (Groq RCA) and `agents/intervention.py` (lever ranking
   over the closed catalog in `agents/levers.py`).
4. `agents/critic.py` gates the ranked plan on one question — does the top
   lever's stated purpose match the diagnosed cause? A second LLM call, skipped
   when the diagnosis is "high" confidence *and* the top score clears
   `CRITIC_SKIP_SCORE`; which path ran is in the `critic_verdict` span. A
   rejection downgrades to the next-ranked lever, or (nothing left) returns
   status `critic_blocked` and writes the do-nothing itself — the client never
   sees that run, so it never reports a decision of its own for it. Rejected
   levers are written `source='suppressed'`, `intensity_rung=NULL`.
   Failure of the critic call itself **fails open** — the top pick is approved.
5. **Delivery layer** (`src/context/InterventionContext.tsx` +
   `src/lib/interventionPolicy.ts` + `src/lib/fatigueBudget.ts`) decides whether the
   ranked plan is worth showing, at what intensity, on which surface. This decision
   is entirely client-side/synchronous (sessionStorage-backed) — it is *reported* to
   the backend after the fact via `POST /api/delivery-decision`, never decided there.

## Persistence (`backend/db.py`, `backend/ledger.py`)

SQLite at `backend/data/app.db` (gitignored, stdlib `sqlite3`, WAL mode), replacing
what used to be process-local dicts in `agents/gate.py` / `agents/memory.py`. Four
tables: `sessions`, `gate_state`, `intervention_events`, `decisions`, `reservations`.

`intervention_events.source` (`ranked` / `delivered` / `suppressed`) exists so three
things that all look like "shown" don't get counted as each other: the top-3 the
ranking agent scored, the one lever the client actually rendered, and levers
considered and withheld. Read `backend/ledger.py`'s module docstring before touching
this table — getting `source` wrong double- or triple-counts the session ledger.

Within `source='suppressed'`, `intensity_rung` separates the two reasons a lever was
withheld: `3` is a rung-3 margin lever the client's policy held back (these are what
`spendAvoidedInr` totals), `NULL` is a critic rejection. Only rung 3 reaches the
ledger panel — the client's sessionStorage copy has no idea critic rejections exist,
so counting them server-side would make the ₹ total jump on rehydration.

`backend/reservations.py` owns the `reservations` table: a 10-minute hold on the
cart's highest-value line when a run crosses the RCA threshold with a `cost_friction`
or `product_uncertainty` diagnosis, released by `POST /api/cart-add` or left to
lapse (expiry is checked at read time, there is no sweeper). `GET
/api/product-availability/{id}?quantity_left=N` subtracts active holds from the
caller-supplied on-hand count — the catalog stays on the frontend.

`GET /api/session-ledger/{id}` rebuilds the ledger panel's state from these tables so
it survives a reload/fresh tab; sessionStorage (`interventionLedger.ts`) is the fast
path, the DB is the durable one. It also reports `silenceRate` — `do_nothing` over
all decisions — which is why every run writes a `decisions` row either way.

## Conventions

- Don't add abstractions/error-handling for cases that can't happen; match the
  terse-docstring, why-not-what comment style already in `backend/db.py` /
  `backend/ledger.py` / `src/lib/fatigueBudget.ts`.
- `RUNG3_ASSUMED_VALUE_INR` is deliberately duplicated in `backend/agents/levers.py`
  and `src/lib/interventionPolicy.ts` — keep both in sync, `tests/test_persistence.py`
  pins the Python side.
- Model metrics are synthetic-data only (see `ml/MODEL_CARD.md`) — never present them
  as production numbers.
- Groq free tier is rate-limited; don't burn it running the RCA pipeline repeatedly
  without cause.
