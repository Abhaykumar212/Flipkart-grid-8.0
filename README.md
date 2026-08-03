# Flipkart GRiD 8.0 — governed cart-abandonment interventions

An offline-first Flipkart storefront clone with real-time event ingestion, calibrated abandonment risk, multi-label root-cause inference, policy-governed interventions, grounded explanations, outcome logging, replay, and an operations dashboard.

The decision path computes 67 versioned features, serves XGBoost models with SHAP evidence, evaluates a closed 12-intervention catalogue through 11 ordered safety rules, ranks approved actions, and persists every outcome—including `NO_ACTION` and `ABSTAIN`. Optional LLM rendering never controls a decision and the full demo works without an API key.

## Why this is judge-ready

- **Useful, not noisy:** the system can intervene, stay silent, or explicitly abstain; fatigue and margin rules override ML confidence.
- **Evidence before prose:** every recommendation is backed by versioned features, calibrated probabilities, SHAP evidence, policy verdicts, and a complete persisted trace.
- **Business-safe learning:** a contextual bandit may reorder only policy-approved actions; discounts require five independent safeguards.
- **Reproducible proof:** eight frozen scenarios cover help, silence, abstention, fatigue, payments, delivery, pricing, and A/B control behavior.
- **Offline by design:** SQLite, deterministic templates, local models, and one-command reset keep the live demo independent of venue Wi-Fi or an API key.

Current synthetic holdout results are ROC-AUC **0.7938**, PR-AUC **0.9254**, ECE **0.0113**, and Brier **0.1468** for risk; root-cause micro-F1 is **0.7850**, macro-F1 **0.7198**, and top-2 recall **0.9771**. See the model cards for limitations and [the verification report](docs/verification-report.md) for the exact release evidence.

## Quick start

Requirements: Python 3.13, Node.js 22, and PowerShell 7+.

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
npm ci
./scripts/train_all.ps1 -Scale full  # only when model .joblib artifacts are absent
./scripts/reset_demo.ps1
./scripts/dev.ps1
```

Open:

- Storefront: http://localhost:5173
- Dashboard: http://localhost:5173/dashboard
- Swagger API: http://localhost:8000/docs
- Runtime readiness: http://localhost:8000/ready
- Runtime metrics: http://localhost:8000/api/v1/metrics

`scripts/dev.ps1` migrates and seeds before starting uvicorn and Vite. SQLite at `data/grid8.db` is the default and requires no external services.

## Deterministic demo

```powershell
./scripts/run_scenario.ps1 A
foreach ($scenario in 'A','B','C','D','E','F','G','H') {
    ./scripts/run_scenario.ps1 $scenario
}
```

Each command asserts the expected cause, intervention, decision, and experiment arm from [the demo script](docs/demo-script.md). It resets the database first, so scenario order cannot affect results.

## Validate

```powershell
./scripts/test.ps1
```

On a clean clone, the test command automatically trains the deterministic
full-scale model artifacts before validation. Subsequent runs reuse them.

For faster focused checks:

```powershell
./.venv/Scripts/python.exe -m pytest tests/unit tests/integration -q
npm test
npm run build
npm run lint
```

## Architecture and guarantees

- React 19 + Vite storefront/dashboard; FastAPI + SQLAlchemy modular monolith.
- 21 strictly validated event types with immutable, idempotent persistence.
- 67-feature schema shared by simulation, training, and serving; intervention features are excluded from risk training.
- Calibrated risk model and 10-label root-cause model with versioned artifacts and rollback-capable registry.
- Policy runs before ranking. A bandit enabled with `RANKER_STRATEGY=bandit` can only reorder already-approved candidates; `rules` is the deterministic default.
- Hindi explanation templates are selected with `Accept-Language: hi`; IDs and numbers are never translated.
- In-process metrics, p50/p95/p99 latency histograms, per-session rate limits, and report-only PSI drift monitoring.
- Session state is rebuildable from the event log; model or LLM failures fail safe.

See [architecture](docs/architecture.md), [API reference](docs/api.md), [data model](docs/data-model.md), [judge demo](docs/demo-script.md), [verification report](docs/verification-report.md), and the [risk](docs/model-card-risk.md) and [root-cause](docs/model-card-root-cause.md) model cards.

## Configuration

Copy `.env.example` to `.env` only when overriding defaults. To use PostgreSQL/Supabase, change `DATABASE_URL`; no code change or alternate migration set is needed. `GROQ_API_KEY` is optional and must never be committed.

The demo uses a documented blended gross-margin assumption of 18%. Model metrics are synthetic holdout results and must not be presented as production performance.
