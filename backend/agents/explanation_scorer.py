"""Explanation grounding scorer — checks whether the JUSTIFICATION TEXT matches
the evidence, not whether the lever choice does.

`agents/critic.py` asks "does the chosen lever's purpose address the diagnosed
cause?" This agent asks a different question: is the prose the RCA agent wrote
to justify that diagnosis (`primary_root_cause.explanation`, each
`why_it_matters`, `confidence_reasoning`, lever `rationale`/`expected_effect`)
actually traceable to a real SHAP signal, or is it a plausible-sounding but
ungrounded narrative? A lever can be perfectly aligned with the cause while the
story told about *why* is invented — that is this agent's failure mode, and the
critic cannot see it because it never reads the prose, only the lever id.

Deliberately narrow: it never re-diagnoses, never touches lever choice, and
only ever runs after the critic has already approved a lever (a critic-blocked
run has nothing worth explaining to a shopper, so main.py skips this agent
entirely on that path).

Provider plumbing is `root_cause.py`'s — same `call_llm` dispatch, same
`RateLimitedError`, same strict-schema shape — so a provider switch stays a
one-line change in `config.py`, exactly like `critic.py`.

Cost control, in order:
  - Runs only when `config.EXPLANATION_SCORER_ENABLED` and the run reached this
    agent at all (i.e. never on `critic_blocked`).
  - One call scores the whole justification trail against the real evidence at
    once, not per-field.
  - A flagged claim earns exactly one regenerate call — never a second scoring
    call to check the regeneration. Whether the rewrite actually improved
    things is verified deterministically (a cheap substring check against the
    real evidence), not with a third LLM call, because this repo's Groq free
    tier is rate-limited and a verification pass doesn't need the nuance a full
    scoring call would spend on it.
  - A rate limit or provider error on the *first* call fails open — the
    explanation is trusted as grounded. This is a safety net over an
    already-approved lever's narrative; losing that narrative to a quota blip
    costs more than an unverified paragraph would.
  - A rate limit or error on the *regenerate* call (or a rewrite that still
    doesn't verify) falls back to a template built directly from the evidence,
    no LLM involved — so there is always something grounded to show, even in
    the worst case.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .. import config
from ..schemas import RootCauseAnalysis
from .root_cause import RateLimitedError, _strip_for_gemini, call_llm

# Which branch `score` took, for the span and the tests.
PATH_LLM = "llm"
PATH_UNAVAILABLE = "unavailable"
PATH_DISABLED = "disabled"

# The verdict persisted to the ledger and shown in the frontend badge.
VERDICT_GROUNDED = "grounded"
VERDICT_REGENERATED = "regenerated"
VERDICT_TEMPLATE_FALLBACK = "template_fallback"

SCORER_SYSTEM_PROMPT = """You are a grounding auditor for an e-commerce cart-recovery system.

A diagnosis agent has written prose explaining why a shopper is hesitating, and that prose is supposed to be traceable to a model's SHAP attribution. Your only job is to check GROUNDING: does every specific claim in the justification text trace back to a real signal and observed value in the evidence provided?

Rules:
1. Take the diagnosis and evidence as given. Do not judge whether the diagnosis is correct, only whether the text justifying it cites real evidence.
2. A claim is grounded when it names a specific signal or observed value that appears in the evidence list, or is a direct, narrow restatement of one.
3. A claim is unsupported when it asserts something the evidence doesn't show — a plausible-sounding generalization, an invented number, a motive or emotion attributed to the shopper without a signal behind it, or a category label used as if it were itself evidence.
4. List each unsupported claim verbatim (or near-verbatim) from the text under review, so it can be located and rewritten.
5. Set `confidence` between 0 and 1: how sure you are in this grounding judgment itself.

Respond only with JSON matching the provided schema."""

REGENERATE_SYSTEM_PROMPT = """You are rewriting a root-cause explanation that was flagged as ungrounded.

Rewrite ONLY the `explanation` field, in 1-2 sentences. Every claim in your rewrite must directly quote or closely paraphrase a specific signal name or observed value from the ground-truth evidence provided — do not paraphrase away the specifics, and do not introduce any claim not covered by that evidence list. If the evidence doesn't support a claim from the original text, drop it rather than keep it.

Respond only with JSON matching the provided schema."""

# Enough evidence items to make a real check possible without an oversized
# prompt — mirrors `critic.build_prompt`'s `[:3]` slice for the same reason.
_PROMPT_EVIDENCE_LIMIT = 5
_VERIFY_TOP_N = 3
_MIN_GROUNDED_MATCHES = 1


@dataclass
class ExplanationScoreResult:
    """One scoring pass. `verdict` is `None` only when the agent was disabled."""

    path: str
    verdict: Optional[str]
    unsupported_claims: List[str] = field(default_factory=list)
    confidence: Optional[float] = None
    detail: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"


def _score_response_schema() -> Dict[str, Any]:
    """Strict schema for the grounding verdict. Same constraints as the critic's:
    `additionalProperties: false` everywhere, every property required."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "grounded": {"type": "boolean"},
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
        },
        "required": ["grounded", "unsupported_claims", "confidence"],
    }


def _regenerate_response_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"explanation": {"type": "string"}},
        "required": ["explanation"],
    }


def _evidence_lines(evidence: List[Dict[str, Any]]) -> str:
    return "\n".join(
        f"  - {item.get('label', item['signal'])} ({item['signal']}): "
        f"observed {item['observed_value']}, SHAP {item['shap_contribution']:+.4f} "
        f"— {item['direction']}"
        for item in evidence[:_PROMPT_EVIDENCE_LIMIT]
    )


def build_prompt(analysis: RootCauseAnalysis, evidence: List[Dict[str, Any]]) -> str:
    """The case file: the real evidence, then every justification-bearing field."""
    cause = analysis.primary_root_cause
    why_it_matters = "\n".join(
        f"  - [supporting_evidence.why_it_matters] {item.signal}: {item.why_it_matters}"
        for item in cause.supporting_evidence
    ) or "  - none"
    lever_rationale = "\n".join(
        f"  - [recommended_levers.rationale] {lever.lever_id}: {lever.rationale}\n"
        f"  - [recommended_levers.expected_effect] {lever.lever_id}: {lever.expected_effect}"
        for lever in analysis.recommended_levers
    ) or "  - none"

    return f"""GROUND-TRUTH SHAP EVIDENCE
{_evidence_lines(evidence)}

JUSTIFICATION TEXT UNDER REVIEW

[primary_root_cause.explanation]
{cause.explanation}

[primary_root_cause.supporting_evidence.why_it_matters, per item]
{why_it_matters}

[confidence_reasoning]
{analysis.confidence_reasoning}

[recommended_levers.rationale / expected_effect, per lever]
{lever_rationale}

Flag any claim above that is not backed by a specific signal + observed value in the ground-truth evidence. A claim that merely sounds plausible, or restates a category without citing a number, is unsupported."""


def build_regenerate_prompt(
    analysis: RootCauseAnalysis, evidence: List[Dict[str, Any]], unsupported_claims: List[str]
) -> str:
    cause = analysis.primary_root_cause
    flagged = "\n".join(f"  - {claim}" for claim in unsupported_claims)
    return f"""GROUND-TRUTH SHAP EVIDENCE
{_evidence_lines(evidence)}

ORIGINAL EXPLANATION
{cause.explanation}

CLAIMS FLAGGED AS UNSUPPORTED
{flagged}

Rewrite `explanation` so every claim directly quotes a signal name or observed value from the ground-truth evidence above."""


def call_scorer(prompt: str, model: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    schema = _score_response_schema()
    if config.LLM_PROVIDER == "gemini":
        schema = _strip_for_gemini(schema)
    return call_llm(
        prompt,
        model,
        system_prompt=SCORER_SYSTEM_PROMPT,
        schema=schema,
        schema_name="explanation_score",
        max_tokens=config.EXPLANATION_SCORER_MAX_TOKENS,
        api_key=config.CRITIC_GROQ_API_KEY,
    )


def call_regenerate(prompt: str, model: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    schema = _regenerate_response_schema()
    if config.LLM_PROVIDER == "gemini":
        schema = _strip_for_gemini(schema)
    return call_llm(
        prompt,
        model,
        system_prompt=REGENERATE_SYSTEM_PROMPT,
        schema=schema,
        schema_name="explanation_regenerate",
        max_tokens=config.EXPLANATION_SCORER_REGENERATE_MAX_TOKENS,
        api_key=config.CRITIC_GROQ_API_KEY,
    )


def _verify_grounded_text(
    text: str, evidence: List[Dict[str, Any]], top_n: int = _VERIFY_TOP_N
) -> bool:
    """Case-insensitive substring check: does the rewrite actually quote a real
    evidence item, rather than trusting the model's own self-report?

    Deliberately crude — the point is to avoid a third LLM call, not to
    re-judge grounding with the nuance the first call already spent on it. One
    real match is enough: demanding several exact hits from a small model
    risks a false-negative fallback on an otherwise-good rewrite.
    """
    if not text:
        return False
    lowered = text.lower()
    matches = 0
    for item in evidence[:top_n]:
        signal = str(item["signal"]).lower()
        label = str(item.get("label", "")).lower()
        observed = str(item["observed_value"]).lower()
        if signal in lowered or (label and label in lowered) or observed in lowered:
            matches += 1
    return matches >= _MIN_GROUNDED_MATCHES


def _template_explanation(evidence: List[Dict[str, Any]]) -> str:
    """Pure Python, no LLM, unconditionally succeeds — the worst-case fallback
    so there is always something grounded to show."""
    top = evidence[:3]
    if not top:
        return "This diagnosis is based on the model's SHAP attribution for this session."
    parts = [
        f"{item.get('label', item['signal'])} (observed {item['observed_value']}) {item['direction']}"
        for item in top
    ]
    return "Grounded directly in the model's attribution: " + "; ".join(parts) + "."


def score(analysis: RootCauseAnalysis, evidence: List[Dict[str, Any]], recorder: Any) -> ExplanationScoreResult:
    """Score the justification trail against the real evidence.

    Mutates `analysis.primary_root_cause.explanation` in place when the text is
    rewritten or replaced, so the corrected text is what ships to the shopper-
    facing report, not just what's recorded in the trace.
    """
    from ..trace import Stage, Status

    if not config.EXPLANATION_SCORER_ENABLED:
        detail = {"path": PATH_DISABLED, "verdict": None, "llm_call": False}
        recorder.add(
            Stage.EXPLANATION_SCORED,
            "Explanation scorer disabled — unreviewed",
            status=Status.SKIPPED,
            detail=detail,
        )
        return ExplanationScoreResult(path=PATH_DISABLED, verdict=None, detail=detail, status=Status.SKIPPED)

    prompt = build_prompt(analysis, evidence)
    started = time.time()
    try:
        parsed, usage = call_scorer(prompt, config.RCA_MODEL)
    except RateLimitedError as error:
        return _fail_open(recorder, Status.RATE_LIMITED, str(error), started)
    except Exception as error:  # noqa: BLE001 - reported in the span, never raised
        return _fail_open(recorder, Status.ERROR, str(error), started)

    unsupported = [str(claim) for claim in parsed.get("unsupported_claims") or []]
    confidence = float(parsed.get("confidence", 0.0))
    detail: Dict[str, Any] = {
        "path": PATH_LLM,
        "model": config.RCA_MODEL,
        "grounded_reported": bool(parsed.get("grounded")),
        "unsupported_claims": unsupported,
        "confidence": confidence,
        "regeneration_attempted": False,
        "llm_call": True,
        "scorer_prompt_tokens": usage.get("prompt_tokens"),
        "scorer_completion_tokens": usage.get("completion_tokens"),
    }

    if not unsupported:
        detail["verdict"] = VERDICT_GROUNDED
        recorder.add(
            Stage.EXPLANATION_SCORED,
            "Explanation grounded in SHAP evidence",
            detail=detail,
            duration_ms=(time.time() - started) * 1000.0,
        )
        return ExplanationScoreResult(PATH_LLM, VERDICT_GROUNDED, unsupported, confidence, detail)

    detail["regeneration_attempted"] = True
    status = Status.OK
    new_text: Optional[str] = None
    try:
        regen_prompt = build_regenerate_prompt(analysis, evidence, unsupported)
        regen_parsed, regen_usage = call_regenerate(regen_prompt, config.RCA_MODEL)
        new_text = regen_parsed["explanation"]
        detail["regen_prompt_tokens"] = regen_usage.get("prompt_tokens")
        detail["regen_completion_tokens"] = regen_usage.get("completion_tokens")
    except RateLimitedError as error:
        status = Status.RATE_LIMITED
        detail["regenerate_error"] = str(error)
    except Exception as error:  # noqa: BLE001 - reported in the span, never raised
        status = Status.ERROR
        detail["regenerate_error"] = str(error)

    if new_text is not None and _verify_grounded_text(new_text, evidence):
        verdict = VERDICT_REGENERATED
        analysis.primary_root_cause.explanation = new_text
        detail["final_explanation_source"] = "regenerated"
        label = "Explanation regenerated to quote SHAP evidence directly"
    else:
        verdict = VERDICT_TEMPLATE_FALLBACK
        if new_text is not None:
            detail["regenerated_text_failed_verification"] = True
        analysis.primary_root_cause.explanation = _template_explanation(evidence)
        detail["final_explanation_source"] = "template"
        label = "Explanation still ungrounded after rewrite — template fallback used"

    detail["verdict"] = verdict
    recorder.add(
        Stage.EXPLANATION_SCORED,
        label,
        status=status,
        detail=detail,
        duration_ms=(time.time() - started) * 1000.0,
    )
    return ExplanationScoreResult(PATH_LLM, verdict, unsupported, confidence, detail, status)


def _fail_open(recorder: Any, status: str, error: str, started: float) -> ExplanationScoreResult:
    """Trust the explanation as grounded when the scorer itself couldn't run."""
    from ..trace import Stage

    detail = {"path": PATH_UNAVAILABLE, "verdict": VERDICT_GROUNDED, "error": error, "llm_call": True}
    recorder.add(
        Stage.EXPLANATION_SCORED,
        "Explanation scorer unavailable — treated as grounded",
        status=status,
        detail=detail,
        duration_ms=(time.time() - started) * 1000.0,
    )
    return ExplanationScoreResult(
        path=PATH_UNAVAILABLE, verdict=VERDICT_GROUNDED, detail=detail, status=status
    )
