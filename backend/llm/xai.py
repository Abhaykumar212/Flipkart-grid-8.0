from __future__ import annotations

import json
from typing import Any
import urllib.error
import urllib.request

from backend import config

from .base import LLMUnavailable, RateLimitedError


class XAIClient:
    """Small stdlib X.AI (Grok) client with stdlib urllib."""

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
            raise LLMUnavailable("X.AI API key is not configured")
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        request = urllib.request.Request(
            "https://api.x.ai/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": "flipkart-grid-explain/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429:
                raise RateLimitedError("X.AI rate limit reached") from error
            raise LLMUnavailable(f"X.AI HTTP {error.code}") from error
        except (TimeoutError, urllib.error.URLError) as error:
            raise LLMUnavailable("X.AI request failed or timed out") from error
        try:
            return str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as error:
            raise LLMUnavailable("X.AI returned a malformed response") from error

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
            raise LLMUnavailable("X.AI returned invalid JSON") from error
        if not isinstance(parsed, dict):
            raise LLMUnavailable("X.AI JSON response must be an object")
        return parsed
