# API reference

FastAPI serves the live OpenAPI document at `/openapi.json`, Swagger UI at `/docs`, and ReDoc at `/redoc`. Request models reject unknown fields. HTTP errors use `application/problem+json`.

## Runtime and observability

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Process liveness; always independent of model readiness |
| GET | `/ready` | Database and both promoted-model readiness |
| GET | `/api/v1/metrics` | Counters, latency percentiles, SSE clients, and drift report |
| GET | `/metrics` | Legacy model holdout metrics |
| GET | `/api/pipeline-config` | Public trigger/model configuration |

## Storefront data and sessions

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/products` | List products; optional category filter |
| GET | `/api/v1/products/{slug}` | Product detail and reviews |
| GET | `/api/v1/products/{product_id}/review-summary` | Grounded cached review summary |
| POST | `/api/v1/sessions` | Create a shopping session |
| GET | `/api/v1/sessions/{session_id}` | Current state and 67-feature snapshot |

## Events and decisions

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/events` | Accept one event or `{events:[...]}` batch; returns 202 |
| POST | `/api/v1/sessions/{session_id}/decisions` | Run the governed decision pipeline |
| GET | `/api/v1/sessions/{session_id}/interventions/latest` | Latest authorized intervention or 204 |
| POST | `/api/v1/decisions/{decision_id}/impression` | Record a rendered intervention |
| POST | `/api/v1/decisions/{decision_id}/outcome` | Record click, dismissal, or conversion |

Decision requests are `{ "trigger": "CART_VIEWED", "force": false }`. `Accept-Language: hi` localizes rendered explanation text while IDs and numbers stay unchanged.

## Dashboard and experiments

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/dashboard/sessions` | Active/recent sessions |
| GET | `/api/v1/dashboard/sessions/{session_id}` | Timeline and feature state |
| GET | `/api/v1/dashboard/decisions/{decision_id}` | Full auditable trace; honours `Accept-Language` |
| GET | `/api/v1/dashboard/overview` | Aggregate decision mix, outcomes, and latency percentiles from persisted traces |
| GET | `/api/v1/dashboard/metrics` | Registered model cards |
| GET | `/api/v1/dashboard/stream` | Reconnecting SSE stream |
| GET | `/api/v1/experiments/{experiment_id}/metrics` | Arm metrics, uplift, CI and significance |

`/api/v1/dashboard/overview` is computed from the durable audit trail rather than the
in-process metrics registry, so latency and volume survive an API restart.

## Demo controls

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/demo/scenarios` | Describe the eight frozen proof scenarios |
| POST | `/api/v1/demo/scenarios/{letter}/run` | Replay one scenario through the real decision path |
| POST | `/api/v1/demo/simulate` | Drive synthetic shoppers end to end, outcomes included |

Scenario replay reuses `ingest_events` and `run_decision`, so a passing scenario passes
because production code produced it. Each run mints fresh session identifiers and is
therefore repeatable without a database reset. `simulate` accepts
`{ "sessions": 1-120, "seed": int }` and returns the shopper-response model it applied
alongside the totals, so simulated figures are never mistaken for production evidence.

Legacy Phase-1 endpoints `/api/predict-abandonment` and `/api/root-cause-analysis` remain available for compatibility but are not used by the current storefront pipeline.
