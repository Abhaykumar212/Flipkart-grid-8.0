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

# Benchmarked against the real RCA payload and schema before selection:
#   gpt-oss-120b  strict json_schema, effort=low,  4000 tok -> OK, ~3.8s
#   gpt-oss-120b  strict json_schema, effort=med,  6000 tok -> HTTP 413 (free-tier TPM)
#   gpt-oss-20b   strict json_schema, effort=low,  4000 tok -> schema failure
#   llama-3.3-70b json_schema UNSUPPORTED (json_object only, invents its shape)
RCA_MODEL = os.getenv("RCA_MODEL", "openai/gpt-oss-120b")

# Deliberately empty by default. gpt-oss-20b cannot reliably satisfy this
# schema, so falling back to it would convert a clean "rate limited" signal into
# a confusing schema error. Set explicitly only if you have a model that can.
RCA_FALLBACK_MODEL = os.getenv("RCA_FALLBACK_MODEL", "").strip()

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

# --- Trigger policy ---------------------------------------------------------

# Matches the "high" tier in main._risk_tier. Chosen from the model's own
# holdout threshold table: at 0.80 precision is 0.904 and coverage 40.2%, so
# roughly 9 in 10 analysed sessions genuinely abandon.
RCA_PROBABILITY_THRESHOLD = float(os.getenv("RCA_PROBABILITY_THRESHOLD", "0.80"))

# Cart must be at least this old before analysis; features are unstable before
# then. Mirrors EVIDENCE_WARMUP_MS in the frontend TrackerContext.
RCA_MIN_CART_AGE_SECONDS = float(os.getenv("RCA_MIN_CART_AGE_SECONDS", "10"))

# Re-analyse only when the material feature signature changes, or after this
# cooldown. Without it the 5s frontend poll would fire an LLM call every poll.
RCA_COOLDOWN_SECONDS = float(os.getenv("RCA_COOLDOWN_SECONDS", "90"))

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
