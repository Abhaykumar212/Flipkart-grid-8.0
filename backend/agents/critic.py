"""Critic agent — the last check before an intervention reaches the shopper.

`agents/intervention.py` ranks deterministically over weights, so a lever can win
on score while its stated purpose has nothing to do with the diagnosed cause: a
discount code out-scoring a review summary on a `product_uncertainty` session
still spends margin on a shopper who was never hesitating about price. This
agent asks one narrow question — *does this lever's stated purpose address this
root cause?* — and downgrades to the next-ranked lever when the answer is no.

Deliberately narrow: it does not re-rank, re-diagnose, or propose anything. It
holds the diagnosis fixed and judges alignment, which is the one thing the
deterministic scorer cannot see.

Provider plumbing is `root_cause.py`'s — same `call_llm` dispatch, same
`RateLimitedError`, same strict-schema shape — so a provider switch stays a
one-line change in `config.py`.

Cost control, in order:
  - The call is skipped when the top pick's score and the diagnosis confidence
    both clear `config.CRITIC_SKIP_SCORE` / "high" (`_should_skip`).
  - When it does run, **one** call judges all three ranked levers. Iterating
    per lever would triple the spend on a rate-limited free tier for a question
    the model answers in a single pass.
  - A rate limit or provider error fails *open* — the top pick is approved. The
    critic is a safety net over an already-valid plan; letting a quota blip
    silence a good intervention costs more than the mismatch it would catch.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .. import config
from ..schemas import InterventionPlan, RootCauseAnalysis
from .levers import CATEGORY_DESCRIPTIONS, LEVER_CATALOG, LEVER_IDS
from .root_cause import RateLimitedError, _strip_for_gemini, call_llm

# Which branch `review` took, for the span and the tests.
PATH_SKIPPED = "skipped_high_confidence"
PATH_DISABLED = "disabled"
PATH_LLM = "llm"
PATH_UNAVAILABLE = "unavailable"

SYSTEM_PROMPT = """You are a quality critic for an e-commerce cart-recovery system.

A diagnosis agent has already determined WHY a shopper is hesitating, grounded in a model's SHAP attribution. A ranking agent has then proposed intervention levers. Your only job is to judge ALIGNMENT: does each proposed lever's stated purpose actually address the diagnosed root cause?

Rules:
1. Take the diagnosis as given. Do not re-diagnose, and do not propose levers of your own.
2. Judge purpose against cause, not general merit. A well-designed lever aimed at the wrong friction is misaligned, however effective it would be elsewhere.
3. Each lever lists the root-cause categories it is designed to address. A lever that does not address the diagnosed category is misaligned unless the evidence clearly shows it resolves that specific friction anyway.
4. Spending margin (discounts, fee waivers, paid upgrades) on a cause that is not about cost is a misalignment, not a bonus.
5. Set `alignment` between 0 and 1: 1.0 when the lever directly resolves the diagnosed friction, 0.0 when it addresses something else entirely. Set `aligned` to match your own score.
6. Keep each `reasoning` to one sentence naming the cause and the lever's purpose.

Return a verdict for every lever you are given, in the order given. Respond only with JSON matching the provided schema."""


@dataclass
class CriticVerdict:
    """One critic pass. `rejected` is ordered worst-ranked-first, as reviewed."""

    path: str
    approved_lever_id: Optional[str]
    rejected: List[Tuple[str, str]] = field(default_factory=list)
    detail: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"


def _response_schema() -> Dict[str, Any]:
    """Strict schema for the verdict array. Same constraints as the RCA schema:
    `additionalProperties: false` everywhere, every property required."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "lever_id": {"type": "string", "enum": LEVER_IDS},
                        "aligned": {"type": "boolean"},
                        "alignment": {"type": "number"},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["lever_id", "aligned", "alignment", "reasoning"],
                },
                "minItems": 1,
            }
        },
        "required": ["verdicts"],
    }


def build_prompt(analysis: RootCauseAnalysis, lever_ids: List[str]) -> str:
    """The case file: the diagnosis, its evidence, and each lever's purpose."""
    cause = analysis.primary_root_cause
    evidence_lines = "\n".join(
        f"  - {item.signal}: observed {item.observed_value}, SHAP {item.shap_contribution:+.4f} "
        f"— {item.why_it_matters}"
        for item in cause.supporting_evidence[:3]
    )
    contributing = "\n".join(
        f"  - {factor.category}: {factor.headline}" for factor in analysis.contributing_factors
    ) or "  - none"

    lever_lines = []
    for index, lever_id in enumerate(lever_ids, start=1):
        meta = LEVER_CATALOG[lever_id]
        addresses = ", ".join(meta["addresses"])  # type: ignore[arg-type]
        lever_lines.append(
            f"  {index}. {lever_id} — {meta['description']} "
            f"Designed for: {addresses}. Business cost: {meta['business_cost']}."
        )

    return f"""DIAGNOSED ROOT CAUSE
Category: {cause.category} — {CATEGORY_DESCRIPTIONS[cause.category]}
Headline: {cause.headline}
Explanation: {cause.explanation}
Diagnosis confidence: {analysis.confidence} ({analysis.confidence_reasoning})

SUPPORTING EVIDENCE
{evidence_lines}

CONTRIBUTING FACTORS
{contributing}

PROPOSED LEVERS, in ranked order
{chr(10).join(lever_lines)}

Judge whether each lever's stated purpose addresses the diagnosed root cause."""


def _should_skip(analysis: RootCauseAnalysis, top_score: float) -> bool:
    """No call when the diagnosis is confident and the top pick won decisively.

    Both conditions, not either: a high score on a low-confidence diagnosis is
    exactly the case where a mismatch is most likely, and a high-confidence
    diagnosis whose best lever barely won says the catalog had no good answer.
    """
    return analysis.confidence == "high" and top_score >= config.CRITIC_SKIP_SCORE


def call_critic(prompt: str, model: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Provider call with the critic's own token budget."""
    schema = _response_schema()
    if config.LLM_PROVIDER == "gemini":
        schema = _strip_for_gemini(schema)
    return call_llm(
        prompt,
        model,
        system_prompt=SYSTEM_PROMPT,
        schema=schema,
        schema_name="critic_verdicts",
        max_tokens=config.CRITIC_MAX_TOKENS,
    )


def review(analysis: RootCauseAnalysis, plan: InterventionPlan, recorder: Any) -> CriticVerdict:
    """Approve the highest-ranked lever whose purpose matches the diagnosis.

    Returns `approved_lever_id=None` when nothing passes — the caller turns that
    into a do-nothing decision. `rejected` holds every lever ranked above the
    approved one, each with the critic's reason.
    """
    from ..trace import Stage, Status

    ranked = plan.top_interventions
    if not ranked:
        return CriticVerdict(path=PATH_DISABLED, approved_lever_id=None)

    top = ranked[0]
    lever_ids = [item.lever_id for item in ranked]

    if not config.CRITIC_ENABLED or _should_skip(analysis, top.score):
        path = PATH_DISABLED if not config.CRITIC_ENABLED else PATH_SKIPPED
        detail = {
            "path": path,
            "approved_lever_id": top.lever_id,
            "top_score": top.score,
            "skip_score": config.CRITIC_SKIP_SCORE,
            "diagnosis_confidence": analysis.confidence,
            "llm_call": False,
        }
        recorder.add(
            Stage.CRITIC_VERDICT,
            f"Critic skipped — {top.lever_id} approved without a call",
            status=Status.SKIPPED,
            detail=detail,
        )
        return CriticVerdict(
            path=path, approved_lever_id=top.lever_id, detail=detail, status=Status.SKIPPED
        )

    prompt = build_prompt(analysis, lever_ids)
    started = time.time()
    try:
        parsed, usage = call_critic(prompt, config.RCA_MODEL)
    except RateLimitedError as error:
        return _fail_open(recorder, top.lever_id, Status.RATE_LIMITED, str(error), started)
    except Exception as error:  # noqa: BLE001 - reported in the span, never raised
        return _fail_open(recorder, top.lever_id, Status.ERROR, str(error), started)

    # Index by lever so a provider that reorders or drops one can't misattribute
    # a verdict; anything missing is treated as unjudged and therefore passing.
    scores = {
        item["lever_id"]: float(item["alignment"])
        for item in parsed["verdicts"]
        if item["lever_id"] in LEVER_CATALOG
    }
    reasons = {item["lever_id"]: item["reasoning"] for item in parsed["verdicts"]}

    approved: Optional[str] = None
    rejected: List[Tuple[str, str]] = []
    for lever_id in lever_ids:
        alignment = scores.get(lever_id)
        if alignment is None or alignment >= config.CRITIC_PASS_THRESHOLD:
            approved = lever_id
            break
        rejected.append((lever_id, reasons.get(lever_id, "misaligned with the diagnosed cause")))

    detail = {
        "path": PATH_LLM,
        "model": config.RCA_MODEL,
        "pass_threshold": config.CRITIC_PASS_THRESHOLD,
        "skip_score": config.CRITIC_SKIP_SCORE,
        "top_lever_id": top.lever_id,
        "approved_lever_id": approved,
        "alignment": {lever_id: round(score, 4) for lever_id, score in scores.items()},
        "rejected": [{"lever_id": lever_id, "reason": reason} for lever_id, reason in rejected],
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "llm_call": True,
    }
    label = (
        f"Critic approved {approved}" if approved else "Critic rejected every ranked lever"
    )
    if approved and rejected:
        label = f"Critic downgraded {top.lever_id} -> {approved}"
    recorder.add(
        Stage.CRITIC_VERDICT,
        label,
        detail=detail,
        duration_ms=(time.time() - started) * 1000.0,
    )
    return CriticVerdict(path=PATH_LLM, approved_lever_id=approved, rejected=rejected, detail=detail)


def _fail_open(
    recorder: Any, top_lever_id: str, status: str, error: str, started: float
) -> CriticVerdict:
    """Approve the top pick when the critic itself couldn't run."""
    from ..trace import Stage

    detail = {
        "path": PATH_UNAVAILABLE,
        "approved_lever_id": top_lever_id,
        "error": error,
        "llm_call": True,
    }
    recorder.add(
        Stage.CRITIC_VERDICT,
        f"Critic unavailable — {top_lever_id} approved unreviewed",
        status=status,
        detail=detail,
        duration_ms=(time.time() - started) * 1000.0,
    )
    return CriticVerdict(
        path=PATH_UNAVAILABLE, approved_lever_id=top_lever_id, detail=detail, status=status
    )
