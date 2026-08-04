from __future__ import annotations

import json
import time
from typing import Any
import urllib.error
import urllib.request

from backend import config

from .base import LLMUnavailable, RateLimitedError

#: One retry, briefly. Groq's free tier 429s in bursts and returns transient
#: 5xx/400s often enough that a single failure used to poison a cached review
#: summary for the whole session. Anything longer would stall the decision path.
_RETRY_DELAY_SECONDS = 0.6


class GroqClient:
    """Small stdlib Groq client with the required non-default User-Agent."""

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else config.GROQ_API_KEY
        self._model = model or config.LLM_MODEL

    def _request(
        self,
        prompt: str,
        *,
        max_tokens: int,
        timeout: float,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if not self._api_key:
            raise LLMUnavailable("GROQ_API_KEY is not configured")
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "reasoning_effort": "low",
        }
        if response_format is not None:
            payload["response_format"] = response_format
        request = urllib.request.Request(
            f"{config.GROQ_BASE_URL}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                # Groq's Cloudflare edge rejects urllib's default UA.
                "User-Agent": "flipkart-grid-explain/1.0",
            },
        )
        body = None
        for attempt in range(2):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = json.load(response)
                break
            except urllib.error.HTTPError as error:
                if attempt == 0 and error.code in (429, 500, 502, 503):
                    time.sleep(_RETRY_DELAY_SECONDS)
                    continue
                if error.code == 429:
                    raise RateLimitedError("Groq rate limit reached") from error
                raise LLMUnavailable(f"Groq HTTP {error.code}") from error
            except (TimeoutError, urllib.error.URLError) as error:
                if attempt == 0:
                    time.sleep(_RETRY_DELAY_SECONDS)
                    continue
                raise LLMUnavailable("Groq request failed or timed out") from error
        try:
            return str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as error:
            raise LLMUnavailable("Groq returned a malformed response") from error

    def generate_text(self, prompt: str, max_tokens: int, timeout: float) -> str:
        return self._request(prompt, max_tokens=max_tokens, timeout=timeout)

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
        timeout: float,
    ) -> dict[str, Any]:
        content = self._request(
            prompt,
            max_tokens=max_tokens,
            timeout=timeout,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "grounded_response", "strict": True, "schema": schema},
            },
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMUnavailable("Groq returned invalid JSON") from error
        if not isinstance(parsed, dict):
            raise LLMUnavailable("Groq JSON response must be an object")
        return parsed

