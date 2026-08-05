"""On-demand translation for the multilingual intervention system.

Two of the three pieces of text an intervention card shows are static per
lever (`headline`, the action button label) — those are translated instantly
on the frontend from a hand-authored dictionary
(`src/lib/interventionTranslations.ts`), no network call needed. `rationale`
is the one dynamic field: it's frequently LLM-personalised per session
(`agents/intervention.py`'s `_to_recommended`), so a static dictionary can't
cover it. This module is what translates *that* — a small, cached, best-effort
Groq call, never on the critical path for showing the card (the frontend
always has the English text to show immediately and swaps the translation in
when/if it arrives).

Caching is process-local and unbounded-but-tiny (a handful of lever rationale
strings × 2 non-English languages, for the lifetime of one demo session) — not
worth a table in `db.py` for what amounts to a few dozen short strings.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from typing import Dict, Optional, Tuple

from . import config

LANGUAGE_NAMES: Dict[str, str] = {
    "hi": "Hindi",
    "ta": "Tamil",
}

_cache: Dict[Tuple[str, str], str] = {}

TRANSLATE_MODEL = "llama-3.1-8b-instant"  # small/fast — this is a one-line translation, not reasoning


def _cache_key(text: str, lang: str) -> Tuple[str, str]:
    return (hashlib.sha1(text.encode("utf-8")).hexdigest(), lang)


def translate_text(text: str, target_lang: str) -> Optional[str]:
    """Best-effort translation. Returns None on any failure — the caller
    already has English text to fall back to, so a silent miss here is a
    non-event, not an error worth surfacing to the shopper.
    """
    language_name = LANGUAGE_NAMES.get(target_lang)
    if not language_name or not text.strip():
        return None

    key = _cache_key(text, target_lang)
    if key in _cache:
        return _cache[key]

    api_key = config.COMPANION_GROQ_API_KEY or config.GROQ_API_KEY
    if not api_key:
        return None

    body = json.dumps(
        {
            "model": TRANSLATE_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"Translate the given e-commerce UI text into natural, "
                        f"conversational {language_name}, written in {language_name} script. "
                        "Return ONLY the translation, nothing else — no quotes, no notes."
                    ),
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
            "max_tokens": 200,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{config.GROQ_BASE_URL}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "flipkart-grid-translate/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.load(response)
            translated = payload["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, TimeoutError):
        return None

    _cache[key] = translated
    return translated


__all__ = ["translate_text", "LANGUAGE_NAMES"]
