# GRiD 8.0 — Intelligent Cart-Abandonment Intervention System
## Architecture Specification for Implementation Planning

> **Purpose:** This document is the source of truth for an AI planning agent.
> It defines the problem, scope, frozen architectural decisions, required components, data contracts, system behavior, evaluation strategy, and implementation constraints.
> The planning agent must use this document to produce a complete, implementation-ready plan. It must not casually replace the decisions marked **Frozen**.

---

## 1. Problem Summary

Build an intelligent, real-time system that observes an active e-commerce session and decides:

1. How likely the customer is to abandon the cart.
2. The most likely root cause of hesitation.
3. The most suitable personalized intervention.
4. The confidence in that recommendation.
5. A human-readable explanation connecting observed evidence to the chosen action.

The system must move beyond generic reminders and blanket coupons. It should behave like a helpful shopping assistant: context-aware, timely, cost-conscious, explainable, and non-intrusive.

### Required final output per decision

```json
{
  "session_id": "SESSION-1842",
  "abandonment_probability": 0.82,
  "risk_level": "HIGH",
  "root_causes": [
    {
      "cause": "PRODUCT_QUALITY_UNCERTAINTY",
      "probability": 0.71
    },
    {
      "cause": "PRICE_SENSITIVITY",
      "probability": 0.56
    }
  ],
  "recommended_intervention": {
    "type": "REVIEW_SUMMARY",
    "channel": "INLINE_CARD",
    "reason": "Repeated review revisits indicate unresolved product-quality concerns."
  },
  "evidence": [
    "User viewed 8 similar products.",
    "User opened reviews 3 times.",
    "User returned to the cart 4 times."
  ],
  "confidence_score": 0.91,
  "intervention_cost": "LOW",
  "decision": "INTERVENE"
}
```

---

## 2. Business Objectives

The system must optimize more than raw conversion.

### Primary objectives

- Increase conversion among genuinely hesitant users.
- Select interventions that address the actual cause of hesitation.
- Minimize unnecessary discounting and protect margins.
- Avoid intrusive or repetitive interventions.
- Produce decisions quickly enough to influence the current session.
- Make every recommendation explainable and auditable.
- Record outcomes so intervention effectiveness can improve over time.

### Explicit anti-goals

The system must not:

- Treat every cart as equally risky.
- Treat every abandoning customer as having the same intent.
- Use discounts as the default intervention.
- Allow an LLM to invent user behavior or unsupported evidence.
- Block the real-time decision path on an LLM call.
- show an intervention merely because one can be generated.
- hide uncertainty; `NO_ACTION` and `ABSTAIN` are valid outputs.

---

## 3. Source-Derived Requirements

The original challenge requires the system to consume a multifaceted package of data such as:

- Purchase history
- Previous cart abandonment
- Product category
- Cart value
- Number of products
- Session duration
- Search activity
- Product-page visits
- Delivery availability
- Price changes
- Wishlist history
- Device type
- Time of day
- Optional demographics

It expects:

- Abandonment probability
- Root cause
- Recommended intervention with reason
- Confidence score
- Human-readable explainability
- Multi-agent orchestration
- Real-time processing
- A prediction model
- A recommendation engine
- An explainability module
- A dashboard/UI
- An architecture diagram
- A working demo

Suggested interventions include:

- Delivery reassurance
- Product comparison
- Price-drop notification
- Similar-product recommendation
- Limited-time discount
- EMI suggestion
- Product-review summary
- Wishlist reminder

Suggested bonus areas include:

- Multilingual recommendations
- A/B testing simulation
- Feedback loop for intervention effectiveness

---

# 4. Frozen Architectural Decisions

The following decisions are fixed unless the planning agent identifies a direct contradiction or an implementation impossibility.

## 4.1 Hybrid intelligence architecture — **Frozen**

Use:

- Supervised ML for numerical prediction.
- Controlled root-cause inference for intent diagnosis.
- A governed recommendation engine for intervention selection.
- Deterministic policy constraints for business safety.
- LLMs only for grounded explanations, review summarization, and multilingual rendering.

Do **not** build an LLM-only decision engine.

---

## 4.2 Modular monolith for the hackathon — **Frozen**

The implementation should be one deployable backend with clear internal module boundaries.

Logical modules may later become services, but the MVP must avoid unnecessary microservice complexity.

Recommended backend module boundaries:

```text
backend/
├── event_ingestion/
├── session_state/
├── feature_engine/
├── risk_model/
├── root_cause/
├── recommendation/
├── policy_engine/
├── explainability/
├── review_intelligence/
├── experimentation/
├── feedback/
└── dashboard_api/
```

---

## 4.3 Event-driven real-time session tracking — **Frozen**

All customer behavior must be represented as immutable events.

Minimum event types:

```text
SESSION_STARTED
SEARCH_PERFORMED
PRODUCT_VIEWED
REVIEW_OPENED
REVIEW_DWELL_RECORDED
SIMILAR_PRODUCT_VIEWED
PRODUCT_COMPARED
ITEM_ADDED_TO_CART
ITEM_REMOVED_FROM_CART
CART_VIEWED
DELIVERY_CHECKED
COUPON_SEARCHED
CHECKOUT_STARTED
CHECKOUT_STEP_VIEWED
PAYMENT_FAILED
PAYMENT_METHOD_CHANGED
INTERVENTION_SHOWN
INTERVENTION_CLICKED
INTERVENTION_DISMISSED
ORDER_COMPLETED
SESSION_ENDED
```

The MVP may use an internal event bus or HTTP event endpoint. The architecture should remain compatible with migration to Kafka or another stream platform.

---

## 4.4 Separate abandonment and root-cause prediction — **Frozen**

Do not use one model for both tasks.

### Risk model

Answers:

> How likely is the user to abandon the cart?

Output:

```json
{
  "abandonment_probability": 0.82,
  "risk_band": "HIGH"
}
```

### Root-cause model

Answers:

> Why is the user likely to abandon?

This must support multiple simultaneous causes.

Output:

```json
{
  "root_causes": [
    {
      "cause": "PRODUCT_QUALITY_UNCERTAINTY",
      "probability": 0.71
    },
    {
      "cause": "PRICE_SENSITIVITY",
      "probability": 0.56
    }
  ]
}
```

---

## 4.5 Gradient-boosted trees as primary tabular models — **Frozen**

For structured session and customer data:

- Train logistic regression as an interpretable baseline.
- Train random forest as a second baseline.
- Use gradient boosting as the primary candidate.
- Select the final model using validation metrics and calibration quality.

Deep learning is optional and should not be introduced unless sequence modeling creates a clear measurable advantage.

---

## 4.6 Controlled root-cause taxonomy — **Frozen**

Use the following first-version taxonomy:

1. `PRICE_SENSITIVITY`
2. `PRODUCT_QUALITY_UNCERTAINTY`
3. `CHOICE_OVERLOAD`
4. `DELIVERY_CONCERN`
5. `AFFORDABILITY_OR_EMI_NEED`
6. `CHECKOUT_OR_PAYMENT_FAILURE`
7. `PRODUCT_AVAILABILITY_CONCERN`
8. `LOW_PURCHASE_INTENT`
9. `TRUST_OR_RETURN_POLICY_CONCERN`
10. `SESSION_INTERRUPTION_OR_DISTRACTION`
11. `UNKNOWN`

The system must allow more than one root cause per session.

`UNKNOWN` is required so the system can abstain safely.

---

## 4.7 Governed intervention catalogue — **Frozen**

The recommendation engine must select from a controlled catalogue.

Initial catalogue:

| Intervention ID | Intended use | Relative cost | Intrusiveness |
|---|---|---:|---:|
| `REVIEW_SUMMARY` | Product-quality uncertainty | Low | Low |
| `PRODUCT_COMPARISON` | Choice overload | Low | Low |
| `DELIVERY_REASSURANCE` | Delivery concern | Low | Low |
| `RETURN_POLICY_REASSURANCE` | Trust concern | Low | Low |
| `PRICE_DROP_ALERT` | Price sensitivity | Low | Low |
| `SIMILAR_PRODUCT_RECOMMENDATION` | Price/availability mismatch | Low | Medium |
| `EMI_SUGGESTION` | Affordability concern | Low | Low |
| `ALTERNATE_PAYMENT_METHOD` | Payment difficulty | Low | Low |
| `CHECKOUT_ASSISTANCE` | Checkout failure | Low | Medium |
| `WISHLIST_REMINDER` | Low immediate intent | Low | Low |
| `LIMITED_TIME_DISCOUNT` | Strong verified price sensitivity | High | High |
| `NO_ACTION` | Low risk, low confidence, or fatigue | Zero | Zero |

Each catalogue entry must contain metadata such as:

```json
{
  "id": "REVIEW_SUMMARY",
  "supported_causes": [
    "PRODUCT_QUALITY_UNCERTAINTY"
  ],
  "cost_level": "LOW",
  "intrusiveness": 1,
  "cooldown_minutes": 15,
  "allowed_channels": [
    "INLINE_CARD",
    "ASSISTANT_PANEL"
  ],
  "requires": [
    "review_summary_available"
  ]
}
```

---

## 4.8 Utility-based intervention ranking — **Frozen**

The recommendation engine must optimize expected incremental value, not only relevance.

Conceptual score:

```text
utility(intervention) =
    relevance
  + expected_conversion_uplift
  + user_affinity
  + information_gain
  - direct_cost
  - margin_risk
  - fatigue_penalty
  - intrusiveness_penalty
```

Weights may initially be hand-tuned and later learned from outcome data.

The planning agent must define:

- Exact normalized features.
- Initial weights.
- Score ranges.
- Tie-breaking behavior.
- Audit output showing every score component.
- How the score evolves when feedback data becomes available.

---

## 4.9 Deterministic policy layer — **Frozen**

ML may propose actions, but deterministic rules must approve, downgrade, or reject them.

Minimum policies:

```text
- Do not intervene below the configured risk threshold.
- Do not show a discount below the configured recommendation confidence.
- Do not show more than the configured maximum interventions per session.
- Do not repeat an intervention within its cooldown period.
- Do not continue after repeated dismissals.
- Do not offer EMI below a configurable cart-value threshold.
- Do not offer a coupon if an equivalent coupon is already applied.
- Do not provide delivery reassurance without reliable delivery data.
- Do not show review summaries when no grounded summary exists.
- Do not show any intervention to a completed order.
- Prefer lower-cost interventions when utility scores are close.
```

Policy decisions must be logged with pass/fail reasons.

---

## 4.10 Explicit confidence, abstention, and fallback — **Frozen**

Maintain separate values for:

- Abandonment probability
- Root-cause probability
- Recommendation confidence

Required behavior:

| Risk | Cause confidence | Required behavior |
|---|---|---|
| Low | Any | `NO_ACTION` |
| High | High | Personalized intervention |
| High | Medium | Low-cost informational intervention |
| High | Low | Safe generic assistance or `NO_ACTION` |
| Medium | High | Subtle inline intervention |
| High | Low and discount proposed | Reject or downgrade discount |

`ABSTAIN` and `NO_ACTION` are first-class decisions.

---

## 4.11 LLMs outside the critical path — **Frozen**

The core real-time path is:

```text
event
→ session update
→ feature computation
→ risk inference
→ root-cause inference
→ candidate generation
→ policy filter
→ utility ranking
→ decision
```

LLMs may be used for:

- Grounded natural-language explanation.
- Product-review summarization using retrieved reviews.
- Multilingual rendering.
- Optional conversational shopping-assistant responses.

LLM failure must not block or invalidate the core decision.

Where possible, review summaries should be precomputed and cached.

---

## 4.12 Separate online and historical views — **Frozen**

### Online session state

Optimized for low-latency reads:

- Current cart
- Current product context
- Event counters
- Recent event sequence
- Current risk score
- Current root causes
- Intervention history
- Dismissal count
- Experiment assignment

### Historical store

Optimized for analysis and training:

- Complete event history
- Past purchases
- Past abandonments
- Feature snapshots
- Model predictions
- Decisions
- Interventions
- Outcomes
- Experiment assignments
- Training labels

The MVP may run both locally, but the logical separation must remain clear.

---

## 4.13 Causal synthetic data generation — **Frozen**

Do not generate independent random rows.

Create a session simulator based on latent shopper personas and behavior rules.

Minimum personas:

- Price-sensitive shopper
- Quality-conscious shopper
- Urgent-delivery shopper
- Comparison-heavy shopper
- Casual browser
- Payment-constrained shopper
- High-intent repeat customer
- Distracted mobile shopper

Example causal pattern:

```text
quality-conscious shopper
→ increased review visits
→ longer review dwell time
→ more specification comparisons
→ higher quality-uncertainty label
→ stronger response to review summary
```

The simulator must generate:

- Event streams
- User profiles
- Product/cart context
- Feature snapshots
- Root-cause labels
- Abandonment outcome
- Counterfactual intervention response
- Final conversion outcome
- Discount cost and margin effect

---

## 4.14 Two user interfaces — **Frozen**

### Customer-facing shopping application

Must support the minimum complete journey:

```text
Product listing
→ Product details
→ Reviews
→ Cart
→ Checkout
```

It must be capable of emitting behavior events and displaying contextual interventions.

### Intelligence dashboard

Must expose:

- Live session events
- Derived features
- Model outputs
- Root causes
- Candidate interventions
- Utility score breakdown
- Policy rejections
- Final action
- Confidence
- Evidence trail
- Customer response
- Experiment group
- Model/version metadata

The customer UI proves the experience.
The dashboard proves the intelligence.

---

## 4.15 Outcome logging and experimentation — **Frozen**

Every recommendation decision must be logged, including `NO_ACTION`.

Minimum decision record:

```json
{
  "decision_id": "D101",
  "session_id": "S102",
  "decision_time": "2026-08-01T14:30:00Z",
  "model_versions": {
    "risk": "risk-v1",
    "root_cause": "cause-v1",
    "ranker": "ranker-rules-v1"
  },
  "abandonment_probability": 0.82,
  "root_causes": [],
  "candidate_interventions": [],
  "policy_results": [],
  "selected_intervention": "REVIEW_SUMMARY",
  "recommendation_confidence": 0.91,
  "experiment_group": "PERSONALIZED_V1"
}
```

Minimum outcome record:

```json
{
  "decision_id": "D101",
  "intervention_shown": true,
  "clicked": true,
  "dismissed": false,
  "order_completed": true,
  "time_to_purchase_seconds": 96,
  "discount_cost": 0,
  "estimated_margin": 4180
}
```

---

## 4.16 Rules and ranking first; contextual bandit later — **Frozen**

Core MVP:

```text
root causes
→ candidate generation
→ eligibility policies
→ utility scoring
→ ranked action
```

Bonus evolution:

```text
contextual bandit
→ select among eligible actions
→ observe reward
→ update action preference
```

Possible reward:

```text
reward =
  conversion_value
  - intervention_cost
  - discount_cost
  - dismissal_penalty
  - repeated-intervention penalty
```

The bandit must not be a dependency for a working MVP.

---

# 5. System Components

## 5.1 Customer application

Responsibilities:

- Render product catalogue and shopping flow.
- Maintain anonymous or authenticated session identity.
- Emit well-formed events.
- Display the selected intervention.
- Record clicks, dismissals, and conversions.
- Never display an intervention that the backend has not authorized.

---

## 5.2 Event ingestion module

Responsibilities:

- Validate event schema.
- Add server timestamp.
- Ensure idempotency using `event_id`.
- Reject invalid session transitions where appropriate.
- Persist immutable events.
- Publish event to the session-state updater.
- Return an acknowledgement quickly.

Required event envelope:

```json
{
  "event_id": "E9001",
  "event_type": "REVIEW_OPENED",
  "user_id": "U12",
  "session_id": "S102",
  "product_id": "P45",
  "client_timestamp": "2026-08-01T14:30:00Z",
  "metadata": {
    "source": "PRODUCT_PAGE"
  }
}
```

---

## 5.3 Session-state module

Responsibilities:

- Maintain current cart and recent behavior.
- Update counters and rolling windows.
- Preserve recent event sequence.
- Track intervention fatigue and cooldowns.
- Expose a consistent snapshot to the decision orchestrator.
- Support deterministic session replay for debugging.

Example state:

```json
{
  "session_id": "S102",
  "cart_value": 29999,
  "cart_items": ["P45"],
  "session_duration_seconds": 1080,
  "review_visit_count": 3,
  "similar_products_viewed": 8,
  "cart_product_switch_count": 6,
  "checkout_failures": 0,
  "interventions_shown": 1,
  "dismissal_count": 0,
  "recent_events": []
}
```

---

## 5.4 Feature engine / Feature Agent

Responsibilities:

- Transform state and historical context into model-ready features.
- Produce one canonical feature contract used for both training and inference.
- Prevent training-serving skew.
- Record feature provenance.
- Support feature snapshots at every decision point.

Feature groups:

### User-history features

- Purchase count
- Prior abandonment rate
- Average order value
- Discount usage rate
- Category affinity
- Average session-to-purchase time
- Prior response to each intervention family

### Current-cart features

- Cart value
- Item count
- Product category
- Discount already available
- Delivery estimate
- Price change percentage
- Inventory status
- EMI eligibility

### Session-behavior features

- Session duration
- Product views
- Review visits
- Review dwell time
- Similar products viewed
- Cart-product switches
- Searches
- Price sorts
- Delivery checks
- Checkout starts
- Payment failures
- Idle duration
- Event velocity

### Context features

- Device type
- Time of day
- New versus returning user
- Network quality if simulated
- Referral source
- Experiment group

---

## 5.5 Risk Agent

Responsibilities:

- Load the active risk-model version.
- Produce a calibrated abandonment probability.
- Assign a risk band.
- Return top contributing features.
- Expose inference latency.
- Support offline batch evaluation.

Required output:

```json
{
  "probability": 0.82,
  "risk_band": "HIGH",
  "model_version": "risk-v1",
  "top_factors": [
    {
      "feature": "cart_product_switch_count",
      "direction": "INCREASES_RISK",
      "contribution": 0.18
    }
  ]
}
```

---

## 5.6 Intent / Root-Cause Agent

Responsibilities:

- Predict multiple likely causes.
- Combine model probabilities with deterministic evidence checks where useful.
- Support `UNKNOWN`.
- Avoid claiming a cause without sufficient evidence.
- Return evidence references, not generated stories.

Required output:

```json
{
  "root_causes": [
    {
      "cause": "PRODUCT_QUALITY_UNCERTAINTY",
      "probability": 0.71,
      "evidence_keys": [
        "review_visit_count",
        "review_dwell_time_seconds",
        "similar_products_viewed"
      ]
    }
  ],
  "model_version": "cause-v1"
}
```

---

## 5.7 Candidate generator

Responsibilities:

- Map root causes to valid intervention candidates.
- Add candidates suggested by current cart context.
- Include `NO_ACTION`.
- Attach all catalogue metadata.
- Never invent a new intervention at runtime.

---

## 5.8 Policy engine

Responsibilities:

- Evaluate every candidate.
- Produce structured pass/fail reasons.
- Downgrade unsafe actions where a safer equivalent exists.
- Enforce cooldown, fatigue, eligibility, and confidence rules.

Required output:

```json
{
  "candidate": "LIMITED_TIME_DISCOUNT",
  "status": "REJECTED",
  "reasons": [
    "recommendation_confidence_below_discount_threshold",
    "low_cost_alternative_available"
  ]
}
```

---

## 5.9 Utility ranker / Recommendation Agent

Responsibilities:

- Score all policy-approved candidates.
- Expose score decomposition.
- Prefer lower-cost actions when scores are close.
- Return recommendation confidence.
- Support deterministic output for identical inputs in MVP mode.

Required output:

```json
{
  "selected": "REVIEW_SUMMARY",
  "score": 0.82,
  "confidence": 0.91,
  "score_breakdown": {
    "root_cause_relevance": 0.31,
    "expected_uplift": 0.28,
    "user_affinity": 0.10,
    "direct_cost_penalty": -0.02,
    "fatigue_penalty": -0.03
  }
}
```

---

## 5.10 Explainability module / Explanation Agent

The core explanation must be structured before natural-language generation.

Required explanation object:

```json
{
  "observations": [
    {
      "feature": "similar_products_viewed",
      "value": 8,
      "statement": "The customer viewed 8 similar products."
    },
    {
      "feature": "review_visit_count",
      "value": 3,
      "statement": "The customer reopened reviews 3 times."
    }
  ],
  "inference": {
    "root_cause": "PRODUCT_QUALITY_UNCERTAINTY",
    "statement": "Repeated review visits and comparison activity indicate unresolved product-quality concerns."
  },
  "action": {
    "intervention": "REVIEW_SUMMARY",
    "statement": "A concise review summary addresses the information gap without using a costly discount."
  }
}
```

An optional LLM may render this object naturally, but it must not add unsupported evidence.

---

## 5.11 Review-intelligence module

Responsibilities:

- Store product reviews.
- Retrieve relevant reviews by product and concern.
- Produce pros, cons, recurring themes, and sentiment.
- Ground every summary in retrieved reviews.
- Cache summaries by product and summary version.
- Provide deterministic fallback text when the LLM is unavailable.

---

## 5.12 Decision orchestrator

Responsibilities:

1. Receive decision trigger.
2. Read a consistent session snapshot.
3. Compute features.
4. Run risk inference.
5. Return early when risk is below threshold.
6. Run root-cause inference.
7. Generate candidates.
8. Apply policies.
9. Rank eligible actions.
10. Apply final confidence/fallback gate.
11. Create explanation object.
12. Persist the complete trace.
13. Return the selected action to the frontend.
14. Update the dashboard stream.

It must define:

- Timeouts
- Fallbacks
- Error handling
- Idempotency
- Duplicate-decision suppression
- Trigger conditions
- Decision frequency

---

## 5.13 Experimentation module

Minimum experiment:

```text
Control:
Generic cart reminder or no intervention

Treatment:
Personalized root-cause intervention
```

Track:

- Conversion rate
- Click-through rate
- Dismissal rate
- Time to purchase
- Discount cost
- Revenue
- Estimated margin
- Incremental uplift
- Intervention frequency

The MVP may use simulated outcomes, but assignments and calculations must be real and reproducible.

---

## 5.14 Intelligence dashboard

Required views:

1. Live active sessions.
2. Session event timeline.
3. Current cart and product context.
4. Feature snapshot.
5. Abandonment probability.
6. Root-cause probabilities.
7. Candidate intervention table.
8. Policy pass/fail reasons.
9. Utility score breakdown.
10. Final recommendation and confidence.
11. Explanation trail.
12. User response and conversion outcome.
13. Experiment metrics.
14. Model metrics and versions.
15. Session replay.

---

# 6. End-to-End Decision Flow

```text
1. Customer performs an action.

2. Frontend emits an immutable event.

3. Event ingestion validates and stores it.

4. Session state is updated.

5. Trigger logic decides whether a fresh intervention decision is needed.

6. Feature Agent creates the latest feature vector.

7. Risk Agent predicts abandonment probability.

8. If risk is below threshold:
   - return NO_ACTION,
   - persist trace,
   - update dashboard.

9. Intent Agent predicts one or more root causes.

10. Candidate generator creates possible interventions.

11. Policy engine rejects or downgrades invalid candidates.

12. Utility ranker scores the remaining candidates.

13. Confidence gate:
    - approves the top action,
    - selects a safer fallback,
    - or returns NO_ACTION.

14. Explanation module builds:
    observations → inferred cause → selected action.

15. Decision and trace are persisted.

16. Customer UI receives and renders the intervention.

17. Click, dismiss, purchase, and abandonment outcomes are logged.

18. Dashboard updates.

19. Historical data feeds evaluation and future learning.
```

---

# 7. Trigger Strategy

The system should not run a full decision after every harmless event.

The planning agent must define a trigger policy using events such as:

- Cart opened after hesitation signals.
- Multiple product comparisons.
- Repeated review visits.
- Long idle time after cart addition.
- Delivery check.
- Checkout initiation.
- Payment failure.
- Back-navigation from checkout.
- Cart value or price change.
- A configurable time interval while risk remains elevated.

The trigger strategy must include:

- Debounce window.
- Minimum time between decisions.
- State-change threshold.
- Duplicate-decision suppression.
- Session termination behavior.

---

# 8. Decision API Contracts

The planning agent may refine naming, but it must preserve the semantics.

## 8.1 Ingest event

```http
POST /api/v1/events
```

Request:

```json
{
  "event_id": "E9001",
  "event_type": "REVIEW_OPENED",
  "user_id": "U12",
  "session_id": "S102",
  "product_id": "P45",
  "client_timestamp": "2026-08-01T14:30:00Z",
  "metadata": {}
}
```

---

## 8.2 Get current session state

```http
GET /api/v1/sessions/{session_id}
```

---

## 8.3 Request or inspect decision

```http
POST /api/v1/sessions/{session_id}/decisions
```

Optional body:

```json
{
  "trigger": "CART_VIEWED",
  "force": false
}
```

---

## 8.4 Get latest intervention

```http
GET /api/v1/sessions/{session_id}/interventions/latest
```

---

## 8.5 Record intervention outcome

```http
POST /api/v1/decisions/{decision_id}/outcome
```

---

## 8.6 Dashboard stream

Use Server-Sent Events or WebSocket for:

```http
GET /api/v1/dashboard/stream
```

The planning agent must choose one and justify it.

---

# 9. Data Model

The implementation plan must define schemas and migrations for at least:

- `users`
- `products`
- `product_reviews`
- `sessions`
- `carts`
- `cart_items`
- `events`
- `session_feature_snapshots`
- `model_predictions`
- `decision_traces`
- `intervention_catalogue`
- `intervention_impressions`
- `intervention_outcomes`
- `experiments`
- `experiment_assignments`
- `orders`
- `model_registry`

The plan must explicitly define:

- Primary keys
- Foreign keys
- Unique constraints
- Indexes
- Retention strategy
- Timestamps
- JSON versus relational fields
- Model/version lineage

---

# 10. Synthetic Data and Model Training

## 10.1 Simulator requirements

The simulator must:

- Use seeded randomness.
- Support configurable number of users and sessions.
- Generate realistic event order.
- Respect causal persona behavior.
- Produce known latent root causes.
- Produce intervention-response probabilities.
- Generate both intervention and no-intervention outcomes.
- Avoid label leakage.
- Export raw events and training tables.
- Support train/validation/test splits by user or time.

## 10.2 Risk-label definition

The planning agent must define exactly:

- What counts as abandonment.
- The observation window.
- The prediction point.
- The label horizon.
- How sessions with no cart are treated.
- How delayed purchases are treated.

## 10.3 Root-cause labels

Because causes are latent, the simulator must preserve the ground-truth persona/cause variables separately from observable features.

## 10.4 Model evaluation

Risk model:

- ROC-AUC
- PR-AUC
- Precision
- Recall
- F1
- Calibration error
- Brier score
- Confusion matrix at chosen threshold

Root-cause model:

- Micro/macro F1
- Per-class precision and recall
- Hamming loss
- Top-k recall
- Coverage of `UNKNOWN`

Recommendation system:

- Root-cause/intervention relevance
- Conversion uplift
- Discount cost
- Margin impact
- Dismissal rate
- Intervention frequency
- Expected utility
- Policy violation count

The planning agent must define target thresholds for the demo.

---

# 11. Explainability Requirements

Every final action must expose:

```text
Observed evidence
→ Model prediction
→ Root-cause inference
→ Candidate actions
→ Policy decisions
→ Utility scores
→ Selected action or NO_ACTION
```

The explanation must answer:

- Why did the system believe abandonment risk was elevated?
- Why was this root cause chosen?
- Why was this intervention selected?
- Why were other interventions rejected?
- Why was a discount not offered?
- What was uncertain?
- Which model and policy versions were used?

---

# 12. User-Experience Constraints

Interventions must:

- Be dismissible.
- Avoid blocking checkout.
- Avoid repeated modal popups.
- Be rendered in a context-appropriate surface.
- Use concise, helpful text.
- Clearly disclose time-limited conditions when relevant.
- Never claim a discount, delivery promise, or product fact that the backend cannot verify.
- Respect cooldown and dismissal history.

Preferred surfaces:

- Inline cart card
- Assistant side panel
- Non-blocking banner
- Comparison drawer
- Checkout assistance panel

Avoid:

- Full-screen interruptions
- Repeated popups
- Artificial urgency
- Misleading scarcity
- Unsupported claims

---

# 13. Suggested Technology Baseline

These are recommended defaults. The planning agent may refine exact libraries while preserving the architecture.

| Layer | Recommended choice |
|---|---|
| Customer UI | React or Next.js |
| Dashboard UI | React or Next.js |
| Backend API | Python FastAPI |
| ML training | Python, scikit-learn, gradient-boosting library |
| Relational store | PostgreSQL |
| Online session state | Redis |
| MVP event transport | HTTP + internal event dispatcher |
| Future event transport | Kafka-compatible stream |
| Model serving | In-process model loading |
| Review retrieval | Local vector index or PostgreSQL vector extension |
| LLM use | Grounded summaries, explanations, multilingual text |
| Local deployment | Docker Compose |
| Dashboard updates | SSE or WebSocket |
| Testing | Unit, integration, end-to-end, model tests |
| Observability | Structured logs, decision traces, latency metrics |

The planning agent must select exact versions and explain dependency choices.

---

# 14. Non-Functional Requirements

The planning agent must define measurable targets for:

## Latency

Suggested targets:

- Event ingestion acknowledgement: under 100 ms locally.
- Risk and root-cause inference: under 100 ms.
- Core decision pipeline: under 300 ms.
- Dashboard update: under 1 second.
- Uncached LLM content: asynchronous and non-blocking.

## Reliability

- Duplicate events must be idempotent.
- Duplicate decisions must be suppressed.
- LLM failure must have a deterministic fallback.
- Redis loss must not destroy historical evidence.
- Model loading failure must fail safely.
- Invalid intervention data must produce `NO_ACTION`.

## Security and privacy

- Avoid storing unnecessary personal data.
- Use synthetic identities in demo data.
- Validate all user-generated metadata.
- Prevent prompt injection from product reviews.
- Keep secrets out of the repository.
- Define environment variables and `.env.example`.

## Reproducibility

- Seeded synthetic data.
- Versioned models.
- Versioned feature schemas.
- Deterministic evaluation scripts.
- One-command local startup.
- One-command test suite.
- One-command demo-data generation.

---

# 15. Required Demo Scenarios

The implementation must support at least these deterministic scenarios:

## Scenario A — Product-quality uncertainty

Behavior:

- Multiple review visits
- Long review dwell time
- Several similar products viewed

Expected:

- High abandonment risk
- Root cause: quality uncertainty
- Intervention: review summary
- Discount rejected

## Scenario B — Delivery concern

Behavior:

- Repeated delivery checks
- Urgent delivery persona
- Product otherwise high intent

Expected:

- Delivery concern
- Delivery reassurance or faster option
- No price discount

## Scenario C — Price sensitivity

Behavior:

- Price sorting
- Coupon search
- Wishlist history
- Price-drop behavior

Expected:

- Price sensitivity
- Price-drop alert first
- Limited-time discount only when confidence and policy permit

## Scenario D — Payment failure

Behavior:

- Checkout started
- Payment failed
- Payment method changed

Expected:

- Checkout/payment failure
- Alternate payment method or checkout assistance

## Scenario E — Low risk

Behavior:

- Direct purchase flow
- Minimal hesitation

Expected:

- `NO_ACTION`
- Explanation that intervention was suppressed

## Scenario F — High risk, low confidence

Behavior:

- Weak or conflicting signals

Expected:

- Safe low-cost fallback or `NO_ACTION`
- No discount

## Scenario G — Fatigue protection

Behavior:

- Two prior dismissals

Expected:

- Further interventions suppressed

## Scenario H — A/B experiment

Expected:

- Same scenario can be assigned to control or personalized treatment.
- Dashboard shows assignment and outcome metrics.

---

# 16. Required Deliverables

The implementation plan must produce all of the following:

1. Working customer-facing shopping flow.
2. Event ingestion and session state.
3. Synthetic event/session generator.
4. Trained abandonment model.
5. Trained multi-label root-cause model.
6. Candidate generator.
7. Policy engine.
8. Utility-based recommendation ranker.
9. Explainability module.
10. Review summarization or grounded fallback.
11. Intelligence dashboard.
12. Outcome logging.
13. A/B testing simulation.
14. Architecture diagram.
15. API documentation.
16. Database schema and migrations.
17. Test strategy and automated tests.
18. Docker-based local environment.
19. Demo scripts and deterministic scenarios.
20. Final README with setup and run commands.

---

# 17. Scope Boundaries

## In scope

- Focused Flipkart-style shopping flow.
- Synthetic products, users, reviews, and sessions.
- Real event emission from the demo frontend.
- Real model training and inference.
- Real policy and ranking decisions.
- Real explanation traces.
- Real dashboard updates.
- Simulated intervention outcomes where necessary.
- Reproducible A/B experiment simulation.

## Out of scope for the MVP

- Full Flipkart clone.
- Real payment processing.
- Real coupon settlement.
- Production-scale Kafka deployment.
- Millions of concurrent sessions.
- Fully autonomous reinforcement learning.
- Unrestricted autonomous agents.
- Real customer PII.
- Complete production fraud, legal, and compliance systems.

---

# 18. Planning Requirements for the Next AI Agent

The planning agent must turn this specification into an implementation-ready plan.

It must:

1. Resolve remaining technical ambiguities.
2. Select exact technologies and versions.
3. Define the complete repository structure.
4. Define all API contracts.
5. Define database schemas and migrations.
6. Define event schemas and state transitions.
7. Define feature definitions precisely.
8. Define model-training and evaluation pipelines.
9. Define decision thresholds and initial utility weights.
10. Define policy rules as executable logic.
11. Define UI routes, components, and interaction flows.
12. Define dashboard views and data sources.
13. Define testing at unit, integration, model, and end-to-end levels.
14. Define deployment and local-development workflow.
15. Break implementation into incremental, runnable phases.
16. End every phase with tests, demo criteria, and a commit boundary.
17. Avoid vague tasks such as “build backend” or “implement AI.”
18. Name likely files and modules for each task.
19. Make reasonable decisions instead of leaving unresolved TODOs.
20. Produce a plan that a separate implementation agent can follow without re-designing the system.

---

# 19. Implementation Philosophy

Each increment must follow this loop:

```text
Observe the current repository
→ document the current state
→ design one small vertical slice
→ implement the slice
→ run it
→ inspect behavior
→ compare with acceptance criteria
→ fix defects
→ test
→ commit
```

Each phase must leave the project runnable.

Prefer vertical slices such as:

```text
frontend event
→ backend ingestion
→ state update
→ decision
→ rendered UI
→ dashboard trace
```

Avoid building all frontend, then all backend, then all ML in isolated blocks.

---

# 20. Definition of Done

The project is done when:

- A user can complete the focused shopping flow.
- Real UI actions generate events.
- Session state updates correctly.
- Risk and root-cause models run on the latest features.
- Policies and utility ranking select or suppress an intervention.
- The selected intervention appears in the customer UI.
- The dashboard exposes the complete reasoning trail.
- Outcomes are recorded.
- Required scenarios behave deterministically.
- Model and system metrics are visible.
- The system runs locally from documented commands.
- Automated tests pass.
- The architecture diagram matches the implementation.
- No core decision depends on a successful LLM call.
