"""Environment-backed runtime settings; defaults are documented in `.env.example`."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _text(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _integer(name: str, default: int) -> int:
    return int(_text(name, str(default)))


def _number(name: str, default: float) -> float:
    return float(_text(name, str(default)))


def _flag(name: str, default: bool) -> bool:
    return _text(name, "1" if default else "0").lower() not in {"0", "false", "no", ""}


# Database and API
DATABASE_URL = _text("DATABASE_URL", "sqlite:///./data/grid8.db")
API_HOST = _text("API_HOST", "0.0.0.0")
API_PORT = _integer("API_PORT", 8000)
CORS_ORIGINS = tuple(
    origin.strip()
    for origin in _text("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
)
LOG_LEVEL = _text("LOG_LEVEL", "INFO").upper()

# Decision thresholds
RISK_INTERVENTION_THRESHOLD = _number("RISK_INTERVENTION_THRESHOLD", 0.40)
RISK_HIGH_THRESHOLD = _number("RISK_HIGH_THRESHOLD", 0.70)
MIN_RECOMMENDATION_CONFIDENCE = _number("MIN_RECOMMENDATION_CONFIDENCE", 0.55)
PERSONALIZED_CONFIDENCE = _number("PERSONALIZED_CONFIDENCE", 0.75)
DISCOUNT_MIN_CONFIDENCE = _number("DISCOUNT_MIN_CONFIDENCE", 0.75)
DISCOUNT_MIN_PRICE_SENSITIVITY = _number("DISCOUNT_MIN_PRICE_SENSITIVITY", 0.60)
DISCOUNT_MIN_CART_VALUE = _number("DISCOUNT_MIN_CART_VALUE", 1000)
DEFAULT_DISCOUNT_PCT = _number("DEFAULT_DISCOUNT_PCT", 7.5)
EMI_MIN_CART_VALUE = _number("EMI_MIN_CART_VALUE", 5000)
MAX_INTERVENTIONS_PER_SESSION = _integer("MAX_INTERVENTIONS_PER_SESSION", 3)
MAX_DISMISSALS = _integer("MAX_DISMISSALS", 2)
UNKNOWN_CAUSE_THRESHOLD = _number("UNKNOWN_CAUSE_THRESHOLD", 0.45)

# Trigger policy and online state
DECISION_DEBOUNCE_SECONDS = _number("DECISION_DEBOUNCE_SECONDS", 3)
MIN_DECISION_INTERVAL_SECONDS = _number("MIN_DECISION_INTERVAL_SECONDS", 20)
PERIODIC_DECISION_SECONDS = _number("PERIODIC_DECISION_SECONDS", 60)
SESSION_TTL_MINUTES = _integer("SESSION_TTL_MINUTES", 30)
SESSION_HARD_TTL_HOURS = _number("SESSION_HARD_TTL_HOURS", 4)
EVENT_DEDUPE_TTL_HOURS = _number("EVENT_DEDUPE_TTL_HOURS", 24)
EVENT_LATE_THRESHOLD_SECONDS = _number("EVENT_LATE_THRESHOLD_SECONDS", 5)
MAX_EVENT_BATCH_SIZE = _integer("MAX_EVENT_BATCH_SIZE", 50)
# Raised from 100: periodic review-dwell reporting means an engaged shopper now
# emits legitimately more events, and a rejected batch still consumes budget on
# retry — so a session that trips this can otherwise never recover in-window.
EVENT_RATE_LIMIT_PER_MINUTE = _integer("EVENT_RATE_LIMIT_PER_MINUTE", 300)
DECISION_RATE_LIMIT_PER_MINUTE = _integer("DECISION_RATE_LIMIT_PER_MINUTE", 20)

# Models
# Share of sessions receiving the personalized arm. A 50/50 pilot split makes a
# live walkthrough a coin flip; 80/20 is the ordinary shape of a rollout that has
# already passed its pilot, and still leaves a real control arm to measure.
EXPERIMENT_TRAFFIC_SPLIT = _integer("EXPERIMENT_TRAFFIC_SPLIT", 80)

# "legacy" is the 22-feature model; "versioned" is the simulator-trained one.
# Legacy is the default because the versioned model's training classes separate
# so cleanly that it saturates near 1.0 on real sessions — see risk_model/legacy.py.
RISK_MODEL_KIND = _text("RISK_MODEL_KIND", "legacy").lower()

RISK_MODEL_VERSION = _text("RISK_MODEL_VERSION", "v1")
ROOT_CAUSE_MODEL_VERSION = _text("ROOT_CAUSE_MODEL_VERSION", "v1")
MODEL_ARTIFACT_DIR = Path(_text("MODEL_ARTIFACT_DIR", "./ml/artifacts"))
RANKER_STRATEGY = _text("RANKER_STRATEGY", "rules").lower()

# Optional LLM renderer
GROQ_API_KEY = _text("GROQ_API_KEY", "")
GROQ_BASE_URL = _text("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
LLM_PROVIDER = _text("LLM_PROVIDER", "groq")
LLM_MODEL = _text("LLM_MODEL", "openai/gpt-oss-120b")
LLM_TIMEOUT_SECONDS = _number("LLM_TIMEOUT_SECONDS", 8)
LLM_MAX_TOKENS = _integer("LLM_MAX_TOKENS", 320)

# Reasoning agent. When enabled and a key is present, the LLM diagnoses the root
# cause and endorses levers; the trained cause model is the fallback. Turning
# this off is also how the model-only path gets demonstrated.
REASONING_LLM_ENABLED = _flag("REASONING_LLM_ENABLED", True)
#: Utility bonus for the agent's top pick. Sits just above `relevance`'s 0.40
#: ceiling so an endorsement leads, without overwhelming cost and fatigue.
REASONING_ENDORSEMENT_WEIGHT = _number("REASONING_ENDORSEMENT_WEIGHT", 0.35)
REASONING_AVOID_PENALTY = _number("REASONING_AVOID_PENALTY", 0.25)

RCA_MODEL = _text("RCA_MODEL", LLM_MODEL)
RCA_FALLBACK_MODEL = _text("RCA_FALLBACK_MODEL", "")
RCA_MAX_TOKENS = _integer("RCA_MAX_TOKENS", 2400)
RCA_REASONING_EFFORT = _text("RCA_REASONING_EFFORT", "low")
RCA_TEMPERATURE = _number("RCA_TEMPERATURE", 0.2)
RCA_TIMEOUT_SECONDS = _number("RCA_TIMEOUT_SECONDS", 30)
RCA_PROBABILITY_THRESHOLD = _number("RCA_PROBABILITY_THRESHOLD", 0.80)
RCA_MIN_CART_AGE_SECONDS = _number("RCA_MIN_CART_AGE_SECONDS", 10)
RCA_COOLDOWN_SECONDS = _number("RCA_COOLDOWN_SECONDS", 90)
# Browsing triggers make decisions frequent, so the cap is a safety net rather
# than the primary economy; the signature cache does most of the saving.
RCA_MAX_PER_SESSION = _integer("RCA_MAX_PER_SESSION", 40)


def groq_is_configured() -> bool:
    return bool(GROQ_API_KEY)


def llm_is_configured() -> bool:
    return bool(GROQ_API_KEY) and LLM_PROVIDER.lower() != "null"


def redacted_key_hint() -> str:
    if not GROQ_API_KEY:
        return "not-set"
    return f"{GROQ_API_KEY[:4]}…{GROQ_API_KEY[-4:]} (len {len(GROQ_API_KEY)})"
