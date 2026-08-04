"""Runtime configuration for the inference and agent services.

Secrets are read from the environment only. `.env` is gitignored; see
`.env.example` for the expected keys. Nothing in this module ever logs or
returns the raw key.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    """Load `.env` if python-dotenv is installed; degrade quietly if not.

    Kept optional so the Phase 1 prediction service still starts on a machine
    where only the ML dependencies are installed.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env")


_load_dotenv()


# --- Groq / LLM -------------------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")

# Optional second key so the companion chat feature doesn't compete with the
# root-cause agent for the same free-tier rate limit. Falls back to the shared
# key if unset, so a single-key setup still works.
COMPANION_GROQ_API_KEY = os.getenv("COMPANION_GROQ_API_KEY", "").strip() or GROQ_API_KEY

# Dedicated key for the post-session re-engagement email drafting agent.
REENGAGEMENT_GROQ_API_KEY = os.getenv("REENGAGEMENT_GROQ_API_KEY", "").strip() or GROQ_API_KEY

# Dedicated key for the real-time Browsing & Search Intent Agent.
BROWSING_AGENT_GROQ_API_KEY = os.getenv("BROWSING_AGENT_GROQ_API_KEY", "").strip() or GROQ_API_KEY
BROWSING_AGENT_MODEL = os.getenv("BROWSING_AGENT_MODEL", "llama-3.3-70b-versatile").strip()

# Benchmarked against the real RCA payload and schema before selection:
#   gpt-oss-120b  strict json_schema, effort=low,  4000 tok -> OK, ~3.8s
#   gpt-oss-120b  strict json_schema, effort=med,  6000 tok -> HTTP 413 (free-tier TPM)
#   gpt-oss-20b   strict json_schema, effort=low,  4000 tok -> schema failure
#   llama-3.3-70b json_schema UNSUPPORTED (json_object only, invents its shape)
GROQ_RCA_MODEL = os.getenv("RCA_MODEL", "openai/gpt-oss-120b")

# Deliberately empty by default. gpt-oss-20b cannot reliably satisfy this
# schema, so falling back to it would convert a clean "rate limited" signal into
# a confusing schema error. Set explicitly only if you have a model that can.
RCA_FALLBACK_MODEL = os.getenv("RCA_FALLBACK_MODEL", "").strip()

# --- Gemini (alternate LLM provider) -----------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
COMPANION_GEMINI_API_KEY = os.getenv("COMPANION_GEMINI_API_KEY", "").strip() or GEMINI_API_KEY
GEMINI_RCA_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Which provider answers RCA + companion chat calls. Both providers implement
# the same (parsed, usage) contract in root_cause.py/companion_chat.py, so this
# is the only switch needed. Defaults to Gemini once a key is present — added
# specifically because Groq's free tier rate-limits hard under demo load.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini" if GEMINI_API_KEY else "groq").strip().lower()

# The model id and fallback surfaced to the frontend / used by analyse() are
# provider-dependent; everything downstream just reads RCA_MODEL.
RCA_MODEL = GEMINI_RCA_MODEL if LLM_PROVIDER == "gemini" else GROQ_RCA_MODEL

# gpt-oss models are reasoning models: reasoning tokens are drawn from the same
# budget as the answer. Too low and the budget is exhausted mid-object, and Groq
# returns "Generated JSON does not match the expected schema" with the tail
# fields missing.
#
# Measured: a full analysis completes in ~830 tokens, so 2400 leaves ~3x
# headroom. Do not raise this casually — `max_tokens` is *reserved* against the
# free tier's 12k tokens/minute, so an inflated value directly reduces how many
# analyses fit in a minute (4000 allowed ~2/min; 2400 allows ~3/min).
RCA_MAX_TOKENS = int(os.getenv("RCA_MAX_TOKENS", "2400"))
RCA_REASONING_EFFORT = os.getenv("RCA_REASONING_EFFORT", "low")
RCA_TEMPERATURE = float(os.getenv("RCA_TEMPERATURE", "0.2"))
RCA_TIMEOUT_SECONDS = float(os.getenv("RCA_TIMEOUT_SECONDS", "30"))


# --- Companion chat ----------------------------------------------------------

# Shares the RCA model by default — already the only tested model that behaves
# predictably against this Groq account. Free-form replies don't need strict
# json_schema, so a different model would work too if you want to split load.
COMPANION_CHAT_MODEL = os.getenv("COMPANION_CHAT_MODEL", RCA_MODEL)
COMPANION_CHAT_MAX_TOKENS = int(os.getenv("COMPANION_CHAT_MAX_TOKENS", "500"))
# Lower than a typical chat temperature on purpose: this endpoint is regularly
# asked to quote exact figures (rating counts, prices) verbatim from context,
# and higher temperatures measurably increased the model paraphrasing those
# numbers instead of copying them.
COMPANION_CHAT_TEMPERATURE = float(os.getenv("COMPANION_CHAT_TEMPERATURE", "0.15"))
COMPANION_CHAT_TIMEOUT_SECONDS = float(os.getenv("COMPANION_CHAT_TIMEOUT_SECONDS", "20"))

# Deliberately small: chat shares the same Groq free-tier budget as the root
# cause agent (see RCA_MAX_TOKENS below for why that ceiling is tight). Keeping
# replies short means a chat session competes less aggressively with the
# recommendation engine for the same tokens/minute allowance.

# --- Critic gate -------------------------------------------------------------

CRITIC_ENABLED = os.getenv("CRITIC_ENABLED", "1").strip().lower() not in ("0", "false", "")

# Skip the critic call entirely when the ranking and the diagnosis already agree
# loudly. Calibrated against `SCORING_WEIGHTS`: a lever that matches the primary
# category (3.0), is the LLM's own first pick (2.0) and carries high confidence
# (1.0) lands around 8.5, while a merely category-matching low-cost lever lands
# around 5.6 — so 7.0 sits between "the agent picked this too" and "the catalog
# happened to match".
CRITIC_SKIP_SCORE = float(os.getenv("CRITIC_SKIP_SCORE", "7.0"))

# A lever passes when the critic's alignment score reaches this. Raising it is
# how you force a downgrade without editing code.
CRITIC_PASS_THRESHOLD = float(os.getenv("CRITIC_PASS_THRESHOLD", "0.5"))

# Far smaller than RCA_MAX_TOKENS: the response is three short verdicts, and
# every token reserved here competes with the analysis for the same per-minute
# free-tier allowance.
CRITIC_MAX_TOKENS = int(os.getenv("CRITIC_MAX_TOKENS", "900"))


# --- Explanation grounding scorer ---------------------------------------------

# Always-on by default, unlike CRITIC_ENABLED's cost/benefit calculus: this
# check only ever runs after the critic has already approved a lever (see
# main.py), so it costs nothing when the run would have been discarded anyway,
# and unlike the critic there's no ranking score to skip it against — every
# grounded-or-not judgment needs the same one call. Still a flag, not a
# hardcoded True, so a quota emergency can turn it off without a code change.
EXPLANATION_SCORER_ENABLED = os.getenv("EXPLANATION_SCORER_ENABLED", "1").strip().lower() not in (
    "0",
    "false",
    "",
)

# Smaller than CRITIC_MAX_TOKENS: the response is a bool, a short claims list,
# and a float — no free-text reasoning field like the critic's `reasoning`.
EXPLANATION_SCORER_MAX_TOKENS = int(os.getenv("EXPLANATION_SCORER_MAX_TOKENS", "500"))

# The regenerate call returns one rewritten paragraph, nothing else — smaller
# still. Only spent when the first call actually flags an unsupported claim.
EXPLANATION_SCORER_REGENERATE_MAX_TOKENS = int(
    os.getenv("EXPLANATION_SCORER_REGENERATE_MAX_TOKENS", "300")
)


# --- Trigger policy ---------------------------------------------------------

# Matches the trigger policy. Lowered to 0.40 for live demo responsiveness.
RCA_PROBABILITY_THRESHOLD = float(os.getenv("RCA_PROBABILITY_THRESHOLD", "0.40"))

# Cart minimum age before analysis. Set to 0.0 for instant demo feedback.
RCA_MIN_CART_AGE_SECONDS = float(os.getenv("RCA_MIN_CART_AGE_SECONDS", "0.0"))

# Re-analyse cooldown. Set to 5.0s for demo.
RCA_COOLDOWN_SECONDS = float(os.getenv("RCA_COOLDOWN_SECONDS", "5.0"))

# Hard per-session budget, independent of the cooldown.
RCA_MAX_PER_SESSION = int(os.getenv("RCA_MAX_PER_SESSION", "10"))


def groq_is_configured() -> bool:
    return bool(GROQ_API_KEY)


def companion_groq_is_configured() -> bool:
    return bool(COMPANION_GROQ_API_KEY)


def redacted_key_hint() -> str:
    """Safe-to-log fingerprint. Never returns the key itself."""
    if not GROQ_API_KEY:
        return "not-set"
    return f"{GROQ_API_KEY[:4]}…{GROQ_API_KEY[-4:]} (len {len(GROQ_API_KEY)})"


# --- Provider-agnostic accessors ---------------------------------------------
# What main.py and the agents actually check — routes to whichever provider
# LLM_PROVIDER selects, so the request handlers don't need to know Groq exists.


def llm_is_configured() -> bool:
    if LLM_PROVIDER == "gemini":
        return bool(GEMINI_API_KEY)
    return groq_is_configured()


def companion_llm_is_configured() -> bool:
    if LLM_PROVIDER == "gemini":
        return bool(COMPANION_GEMINI_API_KEY)
    return companion_groq_is_configured()


def missing_key_hint() -> str:
    """Which env var to set, for the "not configured" message shown in the UI."""
    if LLM_PROVIDER == "gemini":
        return "GEMINI_API_KEY"
    return "GROQ_API_KEY"
