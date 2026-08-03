"""Loading and describing the frozen proof scenarios."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any


SCENARIO_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "scenarios"
SCENARIO_LETTERS = tuple("ABCDEFGH")

#: What each scenario is designed to prove. The fixtures carry the mechanics;
#: this carries the argument, so the UI can state why the scenario exists.
SCENARIO_INTENT: dict[str, dict[str, str]] = {
    "A": {
        "proves": "Evidence-matched help",
        "detail": (
            "Repeated review reading and similar-product browsing diagnose product-quality "
            "uncertainty, so the agent answers the question instead of discounting."
        ),
    },
    "B": {
        "proves": "Intent, not incentive",
        "detail": (
            "Repeated delivery checks route to delivery reassurance. A shopper worried about "
            "shipping is not persuaded by money off."
        ),
    },
    "C": {
        "proves": "Margin protection",
        "detail": (
            "Genuine price sensitivity still does not unlock a discount: the price-drop alert "
            "wins because the discount fails its safety conditions."
        ),
    },
    "D": {
        "proves": "Blocked checkout recovery",
        "detail": (
            "Failed payments diagnose a completion barrier, and the agent offers another way "
            "to pay rather than a reason to buy."
        ),
    },
    "E": {
        "proves": "Restraint",
        "detail": (
            "A low-risk session gets NO_ACTION. Staying silent is a decision the system logs "
            "and defends like any other."
        ),
    },
    "F": {
        "proves": "Honest uncertainty",
        "detail": (
            "High risk with conflicting causes produces ABSTAIN. When the agent cannot say why, "
            "it does not guess an intervention."
        ),
    },
    "G": {
        "proves": "Anti-spam fatigue rules",
        "detail": (
            "A shopper who has already been nudged is left alone. Fatigue policy overrides model "
            "confidence."
        ),
    },
    "H": {
        "proves": "A/B control arm",
        "detail": (
            "The same behaviour produces a generic wishlist reminder in CONTROL and a targeted "
            "review summary in the treatment arm, which is what makes uplift measurable."
        ),
    },
}


@lru_cache(maxsize=None)
def load_fixture(letter: str) -> dict[str, Any]:
    """Load one frozen scenario by its A-H letter."""

    key = letter.strip().upper()
    if key not in SCENARIO_LETTERS:
        raise KeyError(key)
    return json.loads((SCENARIO_DIR / f"{key.lower()}.json").read_text(encoding="utf-8"))


def _expectations(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for session in fixture["sessions"]:
        expected = dict(session.get("expect") or {})
        for action in session["actions"]:
            if action.get("expect"):
                expected.update(action["expect"])
        rows.append({"session_id": session["session_id"], "expected": expected})
    return rows


def scenario_catalogue() -> list[dict[str, Any]]:
    """Describe every scenario without running it."""

    catalogue = []
    for letter in SCENARIO_LETTERS:
        fixture = load_fixture(letter)
        intent = SCENARIO_INTENT[letter]
        catalogue.append({
            "scenario": letter,
            "title": fixture["title"],
            "proves": intent["proves"],
            "detail": intent["detail"],
            "session_count": len(fixture["sessions"]),
            "event_count": sum(
                int(event.get("repeat", 1))
                for session in fixture["sessions"]
                for action in session["actions"]
                for event in action.get("events", [])
            ),
            "expectations": _expectations(fixture),
        })
    return catalogue
