"""AI Shopping Companion — reactive product & review Q&A.

Design intent (see the companion redesign spec): the assistant should already
know the product and its reviews before being asked, and answer with the
confidence of someone who already read everything. This module makes that
literal — the full product context (specs, description, highlights, delivery,
EMI, offers) and its review corpus are stuffed directly into the prompt on
every turn.

Why not retrieval. The per-product corpus here is small (a handful of short
reviews, a short spec sheet) — small enough that handing the model all of it
outperforms retrieving a subset of it, and does so without an embeddings model
or a vector store. Retrieval earns its cost when the corpus is too large to fit
in context; that isn't the case here.

Why not the RCA agent's strict json_schema mode. Chat replies are free text
meant to read naturally, not a structured object Phase 3 has to parse — plain
chat completion is simpler and cheaper.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .. import config
from ..schemas import ChatMessage, ProductContext
from .root_cause import RateLimitedError

SYSTEM_PROMPT = """You are the AI Shopping Companion on an Indian e-commerce platform — a knowledgeable friend shopping alongside the customer, not a customer-support bot.

You have already read the full product listing and every customer review below. Never ask the shopper to repeat information that's already given to you, and never say "let me check" — you already know.

Rules:
1. Answer only from the product context and reviews provided. If something genuinely isn't covered by either, say so plainly rather than guessing.
2. On sentiment questions (battery, camera, durability, "is it worth it"), give a balanced, honest view — real praise and real complaints, both, in plain proportion to how often reviewers actually mention them. A one-sided answer reads as manipulative and undermines trust.
3. For statistical questions ("how many gave 5 stars", "what percent recommend it"), the exact counts and percentages are already computed in the RATING DISTRIBUTION section below — quote them exactly as given. Do not recompute, round, or approximate them yourself; copy the number character-for-character.
4. Never contradict the product context. If a bank offer, coupon, or delivery term is listed below, treat it as true and explain it accurately — never say something isn't available when it's listed.
5. Be concise — two to four sentences unless the question genuinely needs more. No scripted greetings, no re-introducing yourself, no corporate preamble.
5a. Formatting: when the answer is naturally a list of distinct points (specs, pros/cons, comparisons, multiple review themes), write each point on its own line starting with "- " (markdown bullet) instead of folding them into one paragraph — the UI renders these as a real bulleted list. For a single conversational point, just write a plain sentence; don't force a one-item list. Use "**word**" to bold the one or two most decision-relevant terms in a bullet (a spec value, a price, a verdict), not whole sentences.
6. Speak with the confidence of someone who already knows, not a search result being read aloud.
7. If asked about something outside this product entirely, say plainly that it's outside what you can help with here.
8. If a COMPARISON SET is given below, that means the shopper has been actively comparing these specific products this session — you already noticed, they didn't have to ask. Structure a comparison across price, key specs (battery, display, camera, performance), and rating — organized by dimension, not a wall of text per product. Only state a clear winner if the shopper actually asks "which one should I buy" or similar; otherwise stay neutral and let the facts speak.
9. If SEARCH HISTORY is given below, that's what the shopper has actually typed into search this session — real intent, not a guess. If asked "what have I been searching for" or similar, list it back accurately. You can also use it silently to understand what the shopper is generally after, but don't volunteer it unprompted unless it's directly relevant to the question."""


def _format_reviews(reviews: List[Any]) -> str:
    if not reviews:
        return "No reviews available for this product yet."
    lines = []
    for review in reviews[:8]:
        lines.append(f"  - {review.rating:.0f}★ \"{review.title}\": {review.text}")
    return "\n".join(lines)


def _format_specs(specs: List[Any]) -> str:
    if not specs:
        return "  (no structured specifications provided)"
    return "\n".join(f"  - {item.label}: {item.value}" for item in specs[:20])


def _format_rating_distribution(distribution: List[Any], total: int) -> str:
    """Renders exact counts and percentages so stats questions get real
    numbers instead of the model estimating from a handful of sample reviews.
    """
    if not distribution or total <= 0:
        return "  (no rating breakdown provided)"
    ordered = sorted(distribution, key=lambda e: e.stars, reverse=True)
    lines = [
        f"  - {entry.stars}★: {entry.count:,} ratings ({entry.count / total * 100:.0f}%)"
        for entry in ordered
    ]
    positive = sum(e.count for e in ordered if e.stars >= 4)
    lines.append(f"  - {positive / total * 100:.0f}% of all ratings are 4★ or 5★")
    return "\n".join(lines)


def build_product_block(product: ProductContext) -> str:
    """Render the product context the way the prompt consumes it."""
    emi_line = (
        f"EMI available: ₹{product.emi_monthly:.0f}/month for {product.emi_months} months"
        if product.emi_monthly and product.emi_months
        else "No EMI option listed"
    )
    offers_line = "; ".join(product.offers) if product.offers else "No active offers listed"
    highlights_line = "; ".join(product.highlights) if product.highlights else "None listed"

    stock_line = (
        f"In stock ({product.quantity_left} left)" if product.in_stock and product.quantity_left > 0
        else "In stock" if product.in_stock
        else "Out of stock"
    )

    return f"""PRODUCT: {product.title}
Brand: {product.brand} | Category: {product.category}
Price: ₹{product.selling_price:,.0f} (MRP ₹{product.mrp:,.0f})
Availability: {stock_line}
Rating: {product.rating_value:.1f}/5 from {product.rating_count:,} ratings
Delivery: {"Free" if product.delivery_free else "Paid"}, estimated {product.estimated_delivery_days} days
{emi_line}
Offers (bank offers, coupons, cashback, exchange — all currently active): {offers_line}
Seller: {product.seller_name or "unspecified"} (rating {product.seller_rating:.1f}/5)

DESCRIPTION
{product.description or "No description provided."}

HIGHLIGHTS
{highlights_line}

SPECIFICATIONS
{_format_specs(product.specifications)}

RATING DISTRIBUTION (exact — use these numbers for any statistical question)
{_format_rating_distribution(product.rating_distribution, product.rating_count)}

CUSTOMER REVIEWS ({len(product.reviews)} shown, sample only — the distribution above is the complete picture)
{_format_reviews(product.reviews)}"""


def build_comparison_product_block(product: ProductContext, index: int) -> str:
    """Compact per-product block for a comparison set — trimmed relative to the
    single-product view since up to four of these stack in one prompt, and the
    Groq free tier's token budget is already the binding constraint elsewhere
    in this pipeline.
    """
    highlights_line = "; ".join(product.highlights[:5]) if product.highlights else "None listed"
    return f"""[{index}] {product.title}
Brand: {product.brand} | Price: ₹{product.selling_price:,.0f} | Rating: {product.rating_value:.1f}/5 ({product.rating_count:,} ratings)
Highlights: {highlights_line}
Key specs: {"; ".join(f"{s.label}: {s.value}" for s in product.specifications[:8]) or "not listed"}
Delivery: {"Free" if product.delivery_free else "Paid"}, {product.estimated_delivery_days} days | {"In stock" if product.in_stock else "Out of stock"}"""


def build_messages(
    product: Optional[ProductContext],
    history: List[ChatMessage],
    comparison_products: Optional[List[ProductContext]] = None,
    search_history: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """Assemble the full Groq message list: system + product context + conversation."""
    system = SYSTEM_PROMPT
    if product is not None:
        system = f"{SYSTEM_PROMPT}\n\n{build_product_block(product)}"
    else:
        system += "\n\nThe shopper is not currently viewing a specific product. If they ask a product-specific question, ask which product they mean instead of guessing."

    if comparison_products:
        blocks = "\n\n".join(
            build_comparison_product_block(p, i + 1) for i, p in enumerate(comparison_products)
        )
        system += f"\n\nCOMPARISON SET (the shopper has visited all of these this session)\n{blocks}"

    if search_history:
        queries = "\n".join(f"  - \"{q}\"" for q in search_history)
        system += f"\n\nSEARCH HISTORY (most recent first, this session)\n{queries}"

    messages = [{"role": "system", "content": system}]
    messages.extend({"role": turn.role, "content": turn.content} for turn in history)
    return messages


def _messages_to_gemini(messages: List[Dict[str, str]]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """Splits the Groq-shaped message list into (system_instruction, Gemini history).

    Gemini has no "system" role in the turn list — it takes a separate
    `system_instruction` — and uses "model" where Groq/OpenAI use "assistant".
    """
    system_instruction = None
    history: List[Dict[str, Any]] = []
    for message in messages:
        if message["role"] == "system":
            system_instruction = message["content"]
            continue
        role = "model" if message["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [message["content"]]})
    return system_instruction, history


def call_gemini_chat(messages: List[Dict[str, str]], model: str) -> Tuple[str, Dict[str, Any]]:
    """Plain (non-structured) Gemini chat completion. Returns (reply_text, usage)."""
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions

    genai.configure(api_key=config.COMPANION_GEMINI_API_KEY)
    system_instruction, history = _messages_to_gemini(messages)
    gen_model = genai.GenerativeModel(model_name=model, system_instruction=system_instruction)

    try:
        response = gen_model.generate_content(
            history,
            generation_config=genai.GenerationConfig(
                temperature=config.COMPANION_CHAT_TEMPERATURE,
                max_output_tokens=config.COMPANION_CHAT_MAX_TOKENS,
            ),
            request_options={"timeout": config.COMPANION_CHAT_TIMEOUT_SECONDS},
        )
    except google_exceptions.ResourceExhausted as error:
        raise RateLimitedError(str(error)) from error
    except google_exceptions.GoogleAPIError as error:
        raise RuntimeError(f"Gemini error: {error}") from error

    usage_meta = getattr(response, "usage_metadata", None)
    usage = {
        "prompt_tokens": getattr(usage_meta, "prompt_token_count", None),
        "completion_tokens": getattr(usage_meta, "candidates_token_count", None),
    }
    return response.text, usage


def call_groq(messages: List[Dict[str, str]], model: str) -> Tuple[str, Dict[str, Any]]:
    """POST a plain chat completion to Groq. Returns (reply_text, usage)."""
    body = {
        "model": model,
        "messages": messages,
        "temperature": config.COMPANION_CHAT_TEMPERATURE,
        "max_tokens": config.COMPANION_CHAT_MAX_TOKENS,
    }
    request = urllib.request.Request(
        f"{config.GROQ_BASE_URL}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.COMPANION_GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "flipkart-grid-companion-chat/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=config.COMPANION_CHAT_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            detail = json.loads(error.read()).get("error", {}).get("message", "")
        except Exception:
            pass
        if error.code == 429:
            raise RateLimitedError(detail or "Groq rate limit reached") from error
        raise RuntimeError(f"Groq HTTP {error.code}: {detail}") from error

    content = payload["choices"][0]["message"]["content"]
    return content, payload.get("usage", {})


def chat(
    product: Optional[ProductContext],
    history: List[ChatMessage],
    comparison_products: Optional[List[ProductContext]] = None,
    search_history: Optional[List[str]] = None,
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Run one companion chat turn. Returns (reply, metadata)."""
    messages = build_messages(product, history, comparison_products, search_history)
    meta: Dict[str, Any] = {"model_used": None, "latency_ms": 0.0}
    started = time.time()

    # COMPANION_CHAT_MODEL already defaults to config.RCA_MODEL, which is itself
    # provider-aware, so this is the right model id for whichever provider is active.
    model = config.COMPANION_CHAT_MODEL

    try:
        if config.LLM_PROVIDER == "gemini":
            reply, usage = call_gemini_chat(messages, model)
        else:
            reply, usage = call_groq(messages, model)
        meta["model_used"] = model
        meta["latency_ms"] = round((time.time() - started) * 1000, 2)
        meta["prompt_tokens"] = usage.get("prompt_tokens")
        meta["completion_tokens"] = usage.get("completion_tokens")
        return reply, meta
    except RateLimitedError as error:
        meta["error"] = str(error)
        meta["rate_limited"] = True
        return None, meta
    except Exception as error:  # noqa: BLE001 - surfaced to the caller
        meta["error"] = str(error)
        return None, meta
