from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

from backend import config
from backend.llm import LLMClient, client_from_config


SYSTEM_INSTRUCTION = (
    "Rewrite the supplied JSON as 2-3 plain sentences for a retail operations "
    "analyst. Use only facts present in the JSON. Do not add numbers, causes, "
    "or recommendations that are not present. Do not speculate."
)
INJECTION_PATTERN = re.compile(
    r"ignore\s+(?:all\s+)?previous|\bsystem\s*:|\bdeveloper\s*:|\bassistant\s*:|</?review\b",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?%?")
ENUM_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")


def template_prose(explanation: dict[str, Any]) -> str:
    observations = explanation.get("observations", [])
    evidence = " ".join(
        str(item.get("statement", ""))
        for item in observations[:2]
        if isinstance(item, dict) and item.get("statement")
    )
    parts = [
        evidence,
        str(explanation.get("risk", {}).get("statement", "")),
        str(explanation.get("inference", {}).get("statement", "")),
        str(explanation.get("action", {}).get("statement", "")),
    ]
    return " ".join(part for part in parts if part).strip()


def _grounded(prose: str, structured: dict[str, Any]) -> bool:
    source = json.dumps(structured, sort_keys=True, ensure_ascii=False)
    return all(token in source for token in NUMBER_PATTERN.findall(prose)) and all(
        token in source for token in ENUM_PATTERN.findall(prose)
    )


def render_explanation(
    structured: dict[str, Any],
    *,
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """Render only the structured trace; always return a grounded fallback."""

    rendered = deepcopy(structured)
    rendered["rendered_text"] = template_prose(rendered)
    rendered["rendered_by"] = "template"
    source = json.dumps(structured, sort_keys=True, ensure_ascii=False)
    if INJECTION_PATTERN.search(source):
        return rendered
    prompt = (
        f"{SYSTEM_INSTRUCTION}\n\n<structured-explanation>\n"
        f"{source}\n</structured-explanation>"
    )
    try:
        prose = (client or client_from_config()).generate_text(
            prompt,
            max_tokens=config.LLM_MAX_TOKENS,
            timeout=config.LLM_TIMEOUT_SECONDS,
        ).strip()
    except Exception:
        return rendered
    if prose and _grounded(prose, structured):
        rendered["rendered_text"] = prose
        rendered["rendered_by"] = "LLM"
    return rendered
