# Architecture

The application is one React/Vite frontend and one FastAPI modular monolith. SQLite is the offline default; the SQLAlchemy models and Alembic migrations also support PostgreSQL through `DATABASE_URL`.

```mermaid
flowchart TB
    subgraph Web[React storefront and dashboard]
        Store[Storefront routes]
        Events[Validated event emitter]
        Surface[Non-blocking intervention surfaces]
        Dashboard[Dashboard routes]
    end
    subgraph API[FastAPI modular monolith]
        Ingest[event_ingestion]
        State[session_state]
        Features[feature_engine]
        Orchestrator[orchestrator]
        Risk[risk_model]
        Cause[root_cause]
        Candidates[recommendation]
        Policy[policy_engine]
        Explain[explainability]
        Feedback[feedback]
        Experiment[experimentation]
        DashAPI[dashboard_api]
        Observe[observability]
    end
    DB[(SQLite or PostgreSQL\n18 tables)]
    Cache[(In-process TTL SessionStore)]
    Artifacts[(Versioned model artifacts)]

    Store --> Events --> Ingest --> DB
    Ingest --> State --> Cache
    State --> Orchestrator --> Features --> Risk --> Cause --> Candidates --> Policy
    Policy --> Orchestrator --> Explain
    Risk -. load .-> Artifacts
    Cause -. load .-> Artifacts
    Orchestrator --> Surface --> Feedback --> DB
    Orchestrator --> Experiment
    Orchestrator --> Observe
    Orchestrator -. background persist and SSE .-> DashAPI --> Dashboard
```

```mermaid
sequenceDiagram
    participant UI as Storefront
    participant E as Event ingestion
    participant S as Session state
    participant O as Orchestrator
    participant M as Risk + cause models
    participant P as Policy + ranker
    participant X as Explainability
    participant D as Database + SSE

    UI->>E: POST /api/v1/events
    E->>E: validate, rate-limit, deduplicate
    E->>D: append immutable event
    E->>S: apply event
    E-->>UI: 202 Accepted
    UI->>O: POST /sessions/{id}/decisions
    O->>S: compute 67 features
    O->>M: calibrated risk and multi-label causes
    O->>P: generate, govern, then rank
    O->>X: structured grounded explanation
    O-->>UI: decision and authorized surface
    O--)D: persist trace and publish SSE
```

The synchronous decision path never calls an LLM. Optional prose rendering and review summarization have deterministic template fallbacks. `RANKER_STRATEGY=rules` is deterministic; the optional `bandit` strategy only reorders candidates that have already passed policy.

## Reliability boundaries

- Missing risk artifacts yield `ABSTAIN`; readiness returns 503 while liveness stays 200.
- Missing root-cause artifacts yield `UNKNOWN` without hiding the risk result.
- SessionStore eviction rebuilds state from the immutable event stream.
- Trace persistence is after the response and cannot fail the customer decision.
- Duplicate events are ignored by primary-key conflict handling.
- Events and decisions are limited per session to 100/min and 20/min.

## Production evolution (not implemented)

Replace the in-process SessionStore with Redis, the internal event fan-out with Kafka, and SQLite with managed PostgreSQL. Add authentication, distributed rate limiting, separate model serving, and reviewed drift-triggered retraining. These are deployment changes behind current module interfaces, not demo requirements.
