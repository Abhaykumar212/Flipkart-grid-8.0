"""LLM-generated "why buy this now" pitch for the home page's "You were
looking for these" rail.

Deliberately the lightest agent in the codebase: one Groq call, a small fast
model, a short prompt, a deterministic fallback on any failure so the rail
never shows a blank card while waiting on (or after losing) an LLM call. The
frontend caches the result per product for the session, so this fires at most
once per product a shopper actually sees, not on every render.
"""

from __future__ import annotations

import json
from typing import Any, Dict
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .. import config

SYSTEM_PROMPT = """You are writing a short "why buy this now" pitch for a product card on an Indian e-commerce home page, for a shopper who viewed this product earlier and didn't buy.

Write 2-3 short bullet points (each under 12 words) that make a genuine, specific case for buying now — reference the actual price, discount, rating, or category given. No generic hype ("amazing", "must-have"), no fabricated claims (never invent a sale, stock count, or warranty not given to you).

Respond ONLY with JSON: {"bullets": ["...", "...", "..."]}"""


def generate_pitch(product: Dict[str, Any]) -> Dict[str, Any]:
    """Call Groq for a short persuasive bullet list. Falls back to a templated one on any failure."""
    api_key = config.GROQ_API_KEY
    if not api_key:
        return _fallback(product)

    user_prompt = (
        f"Product: {product.get('title')}\n"
        f"Category: {product.get('category')}\n"
        f"Price: ₹{product.get('price')} (MRP ₹{product.get('mrp')}, {product.get('discount_pct')}% off)\n"
        f"Rating: {product.get('rating')}★ from {product.get('rating_count')} ratings\n"
        f"Lowest price in 90 days: {product.get('is_lowest')}\n"
        "Write the pitch now."
    )

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
        "max_tokens": 200,
    }

    url = f"{config.GROQ_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "flipkart-grid-product-pitch/1.0",
    }

    try:
        req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            bullets = [b for b in parsed.get("bullets", []) if isinstance(b, str) and b.strip()][:3]
            if not bullets:
                return _fallback(product)
            return {"status": "success", "bullets": bullets, "source": "llm"}
    except (URLError, HTTPError, TimeoutError, KeyError, ValueError) as error:
        print(f"[ProductPitch] Groq call failed ({error}), using deterministic fallback")
        return _fallback(product)


def _fallback(product: Dict[str, Any]) -> Dict[str, Any]:
    bullets = []
    if product.get("is_lowest"):
        bullets.append("Lowest price in the last 90 days")
    elif product.get("discount_pct", 0) >= 30:
        bullets.append(f"{product.get('discount_pct')}% off right now")
    rating = product.get("rating")
    rating_count = product.get("rating_count", 0)
    if rating and rating >= 4.2 and rating_count >= 500:
        bullets.append(f"Rated {rating}★ by {rating_count:,}+ buyers")
    if not bullets:
        bullets.append("Matched to what you were browsing")
    return {"status": "success", "bullets": bullets, "source": "fallback"}
