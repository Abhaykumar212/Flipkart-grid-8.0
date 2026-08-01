# Phase 2 — Root Cause Analysis Agent

Phase 1 answers *will this cart be abandoned?* (calibrated XGBoost, ROC-AUC
0.8072 at 99.57% of the Bayes ceiling). Phase 2 answers **why**, in a structured
form the next stage can act on.

---

## The design claim we can defend

> "How do you know the LLM isn't just making this up?"

Because it isn't given free rein. The agent receives the **model's own SHAP
attribution** as its evidence base, and the response schema requires it to cite
those signals. It is verbalising the gradient-boosted model's reasoning, not
free-associating over a prompt.

Concretely, a real analysis looked like this:

```
CAUSE      checkout_friction (high confidence)
HEADLINE   Shopper stalled at the start of checkout
EVIDENCE   checkout_steps_completed = 0 of 3 steps      SHAP +0.970
           checkout_friction_events = derived (high)     SHAP +0.578
LEVERS     1. saved_payment_prompt
           2. guest_to_account_nudge
           3. emi_plan_highlight
AVOID      price_drop_alert — no price drop has occurred
```

Every number in the evidence column came from the model, not the LLM.

---

## When it fires

Only at **probability ≥ 0.80**, the model's `high` tier. Taken straight from the
holdout threshold table in `ml/artifacts/metrics.json`:

| threshold | coverage | precision | lift |
|---|---|---|---|
| 0.70 | 54.6% | 0.865 | 1.27x |
| **0.80** | **40.2%** | **0.904** | **1.33x** |
| 0.90 | 21.5% | 0.951 | 1.40x |

At 0.80 roughly nine in ten analysed sessions genuinely abandon, so LLM spend
lands where it pays.

Three further gates (`agents/gate.py`, pure functions, 11 unit tests):

1. **Warm-up** — cart must be ≥10s old; features are unstable before that.
2. **Deduplication** — a hash over *material* features only. Dwell-time ticks
   every second, so hashing the whole vector would re-fire the agent on every
   poll. Re-runs need either a material change or a 90s cooldown.
3. **Session budget** — hard cap of 10 analyses, which even a forced manual
   re-run cannot bypass.

The storefront polls the model every 5s. Without these gates a single demo would
issue thousands of LLM calls; with them it issues roughly one per risk episode.

---

## Model selection — measured, not assumed

Benchmarked against the real payload and schema:

| model | strict `json_schema` | result |
|---|---|---|
| **`openai/gpt-oss-120b`** (`effort=low`, 4000 tok) | ✅ | **chosen** — ~2.4-3.8s |
| `openai/gpt-oss-120b` (`effort=medium`, 6000 tok) | ✅ | HTTP 413 — exceeds free-tier TPM |
| `openai/gpt-oss-20b` (`effort=low`, 4000 tok) | ✅ | fails this schema |
| `llama-3.3-70b-versatile` | ❌ unsupported | `json_object` only, invents its own shape |
| `qwen/qwen3.6-27b` | ❌ unsupported | also failed `json_object` validation |

`gpt-oss-120b` is the only tested model that *guarantees* schema conformance, so
Phase 3 never has to defend against malformed input.

**Two gotchas worth knowing**, both found by testing rather than reading docs:

- These are reasoning models — reasoning tokens come out of the same budget as
  the answer. At `max_tokens=300` the budget is gone before any JSON is emitted;
  at 2000 the object is truncated mid-way and Groq rejects it. 4000 works.
- Groq sits behind Cloudflare, which **403s Python's default urllib
  User-Agent**. The client sets an explicit one.

The automatic fallback model is **off by default**: `gpt-oss-20b` cannot satisfy
this schema, so falling back to it would turn a clean "rate limited" signal into
a confusing schema error.

---

## Output contract (consumed by Phase 3)

```jsonc
{
  "primary_root_cause": {
    "category": "cost_friction | delivery_friction | trust_friction | checkout_friction | product_uncertainty | low_intent",
    "headline": "...",
    "explanation": "...",
    "supporting_evidence": [{ "signal", "observed_value", "shap_contribution", "why_it_matters" }]
  },
  "contributing_factors": [...],
  "shopper_narrative": "plain English for a non-technical operator",
  "confidence": "high | medium | low",
  "confidence_reasoning": "...",
  "recommended_levers": [{ "lever_id", "rationale", "expected_effect", "priority" }],
  "levers_to_avoid":   [{ "lever_id", "reason" }]
}
```

`lever_id` is drawn from a **closed catalog** (`agents/levers.py`), so Phase 3
receives an executable instruction rather than free text. A test asserts every
root-cause category has at least one lever that addresses it — otherwise the
agent could diagnose a problem the system cannot act on.

`levers_to_avoid` is the margin-protection channel: it stops Phase 3 discounting
a shopper who shows no price sensitivity.

---

## Files

```
config.py            env + trigger policy (secrets never logged)
trace.py             span recorder; one span per pipeline stage
schemas.py           shared pydantic contracts
agents/gate.py       trigger policy — pure, unit-tested
agents/levers.py     closed intervention catalog
agents/root_cause.py prompt assembly, Groq call, validation
```

Adding Phase 3 means adding `agents/intervention.py` beside this and one member
to `trace.Stage` — the console renders new stages without modification.

---

## Verification

```bash
python -m unittest tests.test_rca_agent -v      # 33 tests
python -m unittest tests.test_phase1_pipeline   # 12 tests, still green
```

The unit tests deliberately do **not** call Groq — network behaviour is covered
separately. What CI protects is the gate spending budget correctly and malformed
model output being rejected before it reaches the next phase.

---

## Known limitations

1. **`GateStore` is process-local in-memory.** Fine for a single-instance demo;
   production would back it with Redis so state survives restarts and is shared
   across replicas.
2. **Free-tier rate limit is 12k tokens/min — about 3 analyses per minute.**
   `max_tokens` is *reserved* against that ceiling, not just what is consumed:
   a call reserves ~2400 + ~2200 prompt ≈ 4600 tokens even though a real
   analysis only completes in ~830. Exceeding the limit degrades gracefully
   (`status: rate_limited`, ~140ms, no crash, shown as an amber run in the
   console) but **clicking through all six scenarios back-to-back will hit it**.
   Leave ~20s between scenarios during a demo, or upgrade the Groq tier.
3. **SHAP explains the uncalibrated log-odds.** With a calibrator active,
   attributions still rank correctly (isotonic is monotone) but do not decompose
   the calibrated probability itself.
4. **Scenario presets target a category, they don't guarantee it.** The model
   decides; if a preset's cart value dominates, it will correctly say
   `cost_friction` even where the preset was aimed at delivery.
