# PLAN MODE PROMPT — GRiD 8.0 Intelligent Cart-Abandonment System

You are operating in **PLAN MODE**.

Your task is to create a complete, implementation-ready engineering plan for the system described in:

```text
grid8_cart_abandonment_architecture_spec.md
```

Treat that file as the primary source of truth. Read it completely before planning.

Do **not** implement production code in this response. Do not produce a shallow overview. Your output must be detailed enough that a separate implementation AI agent can execute it step by step without re-designing the architecture.

---

## 1. Core objective

Produce a final plan for a working hackathon-grade system that:

- Tracks customer behavior as immutable events.
- Maintains real-time session state.
- Predicts cart-abandonment probability.
- Infers one or more root causes.
- Generates approved intervention candidates.
- Applies deterministic policies.
- Ranks interventions using a utility function.
- Supports `NO_ACTION` and safe fallback behavior.
- Produces a structured and human-readable explanation trail.
- Displays interventions in a focused shopping UI.
- Exposes complete decision traces in an intelligence dashboard.
- Records outcomes and supports an A/B testing simulation.
- Uses synthetic but causally generated data.
- Runs locally with reproducible commands.

---

## 2. Architectural constraints

The architecture specification contains decisions marked **Frozen**.

You must preserve them, especially:

- Hybrid ML + policy + constrained LLM usage.
- Modular-monolith deployment.
- Event-driven session processing.
- Separate risk and multi-label root-cause models.
- Gradient-boosted trees as the main tabular model family.
- Controlled root-cause taxonomy.
- Controlled intervention catalogue.
- Utility-based, cost-aware ranking.
- Deterministic policy and confidence gates.
- `NO_ACTION` and `ABSTAIN`.
- LLMs outside the latency-critical path.
- Separate online session state and historical store.
- Causal synthetic data.
- Customer UI plus intelligence dashboard.
- Complete decision and outcome logging.
- Rules/ranking first; contextual bandit only as a later bonus.

Do not replace these choices with an LLM-only architecture, unconstrained agents, a microservice-heavy MVP, or a generic recommendation system.

When a frozen choice still requires implementation detail, define that detail yourself.

---

## 3. Planning behavior

### Make decisions

Do not leave important matters as:

- “Choose a framework.”
- “Decide later.”
- “Use a database.”
- “Implement suitable model.”
- “Add tests.”
- “Configure deployment.”

Select exact approaches, libraries, modules, data shapes, thresholds, and workflows.

When several valid choices exist:

1. Select one.
2. Explain the reason briefly.
3. Record the rejected alternatives only when the trade-off matters.
4. Continue the plan using the selected choice.

Ask a question only when a missing answer would fundamentally alter the product scope. For ordinary ambiguity, make a sensible assumption and record it.

### No hidden redesign

The implementation agent must not be forced to infer architecture. Define all major contracts and responsibilities now.

### No fake certainty

Clearly label:

- Assumptions
- Frozen decisions
- New decisions made in the plan
- Optional enhancements
- Deferred production concerns

---

## 4. Required output structure

Produce the plan using the following exact top-level structure.

# 1. Executive Implementation Summary

Include:

- What will be built.
- The selected implementation strategy.
- The shortest end-to-end critical path.
- The final deployment shape.
- Why this plan is realistic for a hackathon.

# 2. Decision Log

Create a table with:

- Decision ID
- Decision
- Status: Frozen / Newly selected
- Rationale
- Consequences

Include every major decision required to implement the system.

# 3. Assumptions and Scope

Define:

- MVP scope
- Bonus scope
- Explicit non-goals
- Synthetic-data assumptions
- Demo assumptions
- Single-machine/local deployment assumptions
- What is real versus simulated

# 4. Final System Architecture

Provide:

- A component diagram in Mermaid.
- A sequence diagram for the decision flow.
- A sequence diagram for intervention-outcome logging.
- Module responsibilities.
- Data ownership.
- Synchronous versus asynchronous boundaries.
- Failure and fallback behavior.
- Latency budget per stage.

# 5. Exact Technology Stack

Specify:

- Languages and versions
- Frontend framework and version
- Backend framework and version
- State-management choices
- Database and version
- Redis and version
- ML libraries
- Vector/retrieval approach
- LLM integration strategy
- Testing frameworks
- Linting and formatting
- Containerization
- Package-management strategy
- API documentation
- Dashboard-update mechanism: choose SSE or WebSocket
- Development and production-like commands

Explain every choice briefly.

# 6. Repository Structure

Provide a complete proposed file tree.

The file tree must be detailed enough to show:

- Frontend routes
- Frontend components
- Backend modules
- Domain models
- API routers
- Database migrations
- Event schemas
- Model-training code
- Simulator
- Model artifacts
- Tests
- Docker files
- Scripts
- Documentation
- Demo fixtures

For each major directory, explain its responsibility.

# 7. Domain Model and Database Design

Define every required entity.

For each table include:

- Columns
- Types
- Primary key
- Foreign keys
- Unique constraints
- Indexes
- Important check constraints
- JSON fields and why they are JSON
- Retention considerations
- Model/version lineage

At minimum cover:

- users
- products
- product_reviews
- sessions
- carts
- cart_items
- events
- session_feature_snapshots
- model_predictions
- decision_traces
- intervention_catalogue
- intervention_impressions
- intervention_outcomes
- experiments
- experiment_assignments
- orders
- model_registry

Also define the Redis key model and TTL strategy.

# 8. Event Model

Define:

- Canonical event envelope
- Every event type
- Required metadata per event
- Event validation
- Idempotency
- Ordering assumptions
- Late events
- Duplicate events
- Invalid transitions
- Session start and end
- Event persistence
- Session replay

Provide JSON examples.

# 9. Session State and Feature Engineering

Define the canonical online session-state object.

Then define every model feature precisely:

- Name
- Type
- Source
- Transformation
- Time window
- Default value
- Leakage risk
- Use in risk model, root-cause model, or recommendation layer

Group features into:

- User history
- Cart
- Session behavior
- Product
- Delivery
- Payment
- Context
- Intervention history

Define how training-serving skew is prevented.

# 10. Synthetic Data Generator

Design the simulator completely.

Include:

- Persona definitions
- Product and category generation
- Price and delivery generation
- Event-state machine
- Root-cause generation
- Abandonment-generation logic
- Intervention-response model
- Counterfactual outcome generation
- Discount cost and margin calculation
- Seed handling
- Dataset size
- Export formats
- Train/validation/test split
- Label-leakage prevention
- Validation checks for realism

Provide pseudocode and exact generated datasets/files.

# 11. Machine-Learning Plan

Define separately:

## 11.1 Abandonment model

- Label definition
- Prediction point
- Horizon
- Baselines
- Primary model
- Hyperparameter strategy
- Class imbalance handling
- Calibration
- Threshold selection
- Metrics
- Model persistence
- Inference contract
- Explainability method

## 11.2 Root-cause model

- Multi-label formulation
- Label construction
- One-vs-rest versus native multi-label choice
- `UNKNOWN` handling
- Thresholds per cause
- Metrics
- Evidence attachment
- Model persistence
- Inference contract

## 11.3 Model registry and versioning

- Artifact names
- Metadata
- Feature schema version
- Training-data version
- Promotion criteria
- Rollback

Define target demo metrics.

# 12. Recommendation and Policy Engine

Define:

- Candidate generation
- Root-cause-to-intervention mapping
- Catalogue schema
- Eligibility checks
- Policy evaluation order
- Confidence gates
- Fatigue rules
- Cooldowns
- Discount protection
- Safe fallbacks
- `NO_ACTION`
- Deterministic tie-breaking

Define the exact initial utility formula:

- Inputs
- Normalization
- Weights
- Score range
- Confidence calculation
- Audit breakdown

Provide worked examples for at least:

- Quality uncertainty
- Delivery concern
- Price sensitivity
- Payment failure
- High risk but low confidence
- Repeated dismissals

# 13. Explainability and Review Intelligence

Define:

- Structured explanation schema
- Evidence selection
- Feature contributions
- Root-cause reasoning
- Policy-rejection explanation
- Recommendation explanation
- Natural-language rendering
- LLM prompt boundaries
- Prompt-injection protection
- Review retrieval
- Review-summary caching
- Deterministic fallback
- Multilingual extension

No explanation may contain evidence absent from the structured trace.

# 14. API Design

Define every endpoint with:

- Method and route
- Purpose
- Request schema
- Response schema
- Error cases
- Idempotency behavior
- Authentication assumption
- Example payload

At minimum include:

- Event ingestion
- Session state
- Decision request
- Latest intervention
- Intervention impression
- Outcome recording
- Product catalogue
- Reviews
- Cart
- Checkout simulation
- Dashboard active sessions
- Decision trace
- Experiment metrics
- Dashboard stream

# 15. Frontend Plan

## 15.1 Customer application

Define:

- Routes
- Page responsibilities
- Components
- State flow
- Event-emission locations
- Intervention surfaces
- Dismissal behavior
- Loading and fallback states
- Checkout simulation
- Accessibility considerations

## 15.2 Intelligence dashboard

Define:

- Routes
- Views
- Tables
- Charts
- Live updates
- Session replay
- Decision trace
- Feature display
- Model and policy display
- Experiment metrics

Name the likely components and data hooks.

# 16. Orchestration and Runtime Flow

Define the decision orchestrator step by step.

Include:

- Trigger conditions
- Debouncing
- Minimum decision interval
- Snapshot consistency
- Model timeouts
- LLM timeout
- Duplicate-decision suppression
- Transaction boundaries
- Partial failure handling
- Retry behavior
- Logging
- Trace IDs
- Safe fallback

Provide executable-quality pseudocode.

# 17. Experimentation and Feedback

Define:

- Initial A/B experiment
- Assignment strategy
- Control behavior
- Treatment behavior
- Metrics
- Simulated outcome strategy
- Incremental uplift calculation
- Discount-cost calculation
- Margin calculation
- Feedback data model
- How future contextual-bandit support would fit without blocking MVP

# 18. Testing Strategy

Define:

- Unit tests
- Schema tests
- Event-ordering tests
- Session-state tests
- Feature tests
- Model tests
- Calibration tests
- Policy tests
- Recommendation tests
- Explanation-grounding tests
- API integration tests
- Database tests
- Frontend component tests
- End-to-end tests
- Deterministic demo tests
- Performance tests
- Failure-injection tests

For each category, name representative test cases and likely files.

# 19. Observability, Security, and Reliability

Define:

- Structured log format
- Decision trace correlation
- Metrics
- Latency tracking
- Error tracking
- Model drift placeholders
- Health checks
- Readiness checks
- Secret management
- Input validation
- Prompt-injection protection
- Synthetic-data privacy
- Backup/fallback behavior

# 20. Local Development and Deployment

Define:

- Docker Compose services
- Ports
- Environment variables
- `.env.example`
- Database migration flow
- Seed flow
- Model training flow
- Model-loading flow
- One-command startup
- One-command test
- One-command demo reset
- One-command deterministic scenario run
- CI workflow
- Production-like deployment notes

# 21. Incremental Implementation Phases

This is the most important section.

Break the work into small, runnable phases.

Every phase must contain:

- Phase objective
- User-visible or system-visible outcome
- Prerequisites
- Exact modules/files to create or modify
- Ordered implementation tasks
- API/schema changes
- Tests to add
- Commands to run
- Manual inspection steps
- Acceptance criteria
- Failure cases to verify
- Commit boundary and suggested commit message
- What remains intentionally deferred

Use vertical slices.

A good phase must leave the repository runnable.

Use this loop inside every phase:

```text
Observe repository
→ document state
→ design one slice
→ implement
→ run
→ inspect
→ compare with acceptance criteria
→ fix
→ test
→ commit
```

Do not create vague phases such as:

- “Build backend”
- “Implement ML”
- “Create frontend”
- “Add testing”

Instead, use incremental phases similar to:

1. Repository bootstrap and health checks.
2. Product catalogue and focused shopping shell.
3. Event contract and browser event emission.
4. Event ingestion, persistence, and session state.
5. Deterministic rule-only decision vertical slice.
6. Dashboard decision trace.
7. Synthetic session generator.
8. Risk-model training and inference.
9. Multi-label root-cause model.
10. Controlled intervention catalogue and policy engine.
11. Utility ranker and confidence fallback.
12. Grounded explanation pipeline.
13. Review retrieval and summary.
14. Full intervention rendering and outcome logging.
15. A/B testing simulation.
16. Demo scenarios and system hardening.
17. Bonus multilingual or contextual-bandit extension.

You may refine this sequence, but preserve the principle that each phase is independently testable and demoable.

# 22. Dependency Graph and Critical Path

Show:

- Phase dependencies
- Parallelizable work
- Critical path
- Earliest point at which an end-to-end demo exists
- Earliest point at which ML replaces deterministic stubs
- Earliest point at which the dashboard is useful
- Bonus work that can be cut without harming MVP

# 23. Demo Script

Write the exact final demo flow.

Cover at least:

- Product-quality uncertainty
- Delivery concern
- Price sensitivity
- Payment failure
- Low risk
- High risk/low confidence
- Fatigue protection
- A/B experiment

For each scenario include:

- Initial fixture
- User actions
- Expected events
- Expected model output
- Expected policy result
- Expected intervention
- Expected dashboard trace
- Expected recorded outcome

# 24. Final Acceptance Checklist

Provide a binary checklist covering:

- Functional requirements
- ML requirements
- Recommendation quality
- Explainability
- UX
- Performance
- Reliability
- Tests
- Documentation
- Deployment
- Demo readiness

# 25. Handoff Instructions for the Implementation Agent

End with a concise operating procedure for the implementation agent:

- Which document to read first.
- Which phase to start with.
- How to verify the current repository state.
- How to maintain the decision log.
- How to avoid scope drift.
- When to stop and report a blocker.
- Required test and commit discipline.
- How to update the plan when implementation reality differs.

---

## 5. Quality bar

The plan is unacceptable if it:

- Repeats the architecture specification without converting it into implementation detail.
- Leaves major technology or data choices unresolved.
- Omits schemas, contracts, or file-level structure.
- Uses “AI agent” as a substitute for defined behavior.
- Depends on LLMs for numerical prediction.
- Omits `NO_ACTION`, confidence gates, or discount protection.
- Builds isolated layers instead of vertical slices.
- Gives phases without tests and acceptance criteria.
- Produces a plan that another agent must reinterpret.

The final output should be a durable `IMPLEMENTATION_PLAN.md` suitable for direct execution by another AI coding agent.
