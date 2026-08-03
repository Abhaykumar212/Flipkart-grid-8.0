from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

from backend import config
from backend.llm import LLMClient, client_from_config
from backend.observability.latency import metrics_registry
from .i18n import localized_template, resolve_language


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


def template_prose(explanation: dict[str, Any], language: str = "en") -> str:
    return localized_template(explanation, resolve_language(language))


def _grounded(prose: str, structured: dict[str, Any]) -> bool:
    source = json.dumps(structured, sort_keys=True, ensure_ascii=False)
    return all(token in source for token in NUMBER_PATTERN.findall(prose)) and all(
        token in source for token in ENUM_PATTERN.findall(prose)
    )


def render_explanation(
    structured: dict[str, Any],
    *,
    client: LLMClient | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Render only the structured trace; always return a grounded fallback."""

    rendered = deepcopy(structured)
    target_language = resolve_language(language)
    rendered["rendered_text"] = template_prose(rendered, target_language)
    rendered["rendered_by"] = "template"
    rendered["language"] = target_language
    source = json.dumps(structured, sort_keys=True, ensure_ascii=False)
    if INJECTION_PATTERN.search(source):
        return rendered
    language_instruction = (
        "Render in Hindi while preserving every identifier and number exactly."
        if target_language == "hi"
        else "Render in English."
    )
    prompt = (
        f"{SYSTEM_INSTRUCTION} {language_instruction}\n\n<structured-explanation>\n"
        f"{source}\n</structured-explanation>"
    )
    try:
        prose = (client or client_from_config()).generate_text(
            prompt,
            max_tokens=config.LLM_MAX_TOKENS,
            timeout=config.LLM_TIMEOUT_SECONDS,
        ).strip()
    except Exception:
        metrics_registry.increment("llm_render", label="fallback")
        return rendered
    if prose and _grounded(prose, structured):
        rendered["rendered_text"] = prose
        rendered["rendered_by"] = "LLM"
        metrics_registry.increment("llm_render", label="success")
    else:
        metrics_registry.increment("llm_render", label="fallback")
    return rendered
