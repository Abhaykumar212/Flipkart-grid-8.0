"""Dedicated Browsing & Search Intent Agent.

Consumes real-time user browsing cues (search queries, product views, review scrolling,
dwell times, spec checks) and executes an LLM call via the dedicated BROWSING_AGENT_GROQ_API_KEY
to recommend high-relevance intervention cards and actionable DOM recommendations.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .. import config
from .levers import LEVER_CATALOG

SYSTEM_PROMPT = """You are an intelligent real-time Browsing & Search Intent Agent for Flipkart.
Your goal is to evaluate user browsing behavior (search queries, product detail views, review inspection, dwell times) and select the single best intervention lever from the closed catalog to resolve shopper friction or assist product research.

Catalog of available levers:
- emi_plan_highlight: Highlight No-Cost EMI plans for high-value carts/products.
- review_summary_surface: Surface an AI summary of customer reviews.
- free_delivery_waiver: Offer free delivery waiver for this session.
- targeted_discount_code: Offer a personalized discount code.
- delivery_speed_upgrade: Upgrade to express/faster delivery.
- trust_badge_reassurance: Display payment security and return policy guarantees.
- stock_scarcity_nudge: Display stock scarcity / high demand signals.
- price_drop_alert: Notify about price drops.
- saved_payment_prompt: Prompt to save payment method.

Respond ONLY with valid JSON matching this schema:
{
  "recommended_lever_id": "one of the lever_ids above",
  "headline": "Short, catchy headline (max 10 words)",
  "rationale": "Clear rationale explaining why this intervention addresses the user's intent",
  "action_label": "Button text (e.g. Explore EMI Plans, Read AI Summary, Apply Free Delivery)",
  "action_type": "scroll_to_emi | open_reviews | open_comparison | open_delivery | claim_discount",
  "confidence": "high | medium"
}
"""

def analyze_browsing_intent(cue: Dict[str, Any]) -> Dict[str, Any]:
    """Call Groq using BROWSING_AGENT_GROQ_API_KEY to generate intent-driven interventions."""
    api_key = config.BROWSING_AGENT_GROQ_API_KEY
    if not api_key:
        return _fallback_recommendation(cue)

    cue_type = cue.get("type", "product_view")
    query = cue.get("query", "")
    product_name = cue.get("product_name", "")
    price = cue.get("price", 0)
    dwell_seconds = cue.get("dwell_seconds", 0)

    user_prompt = f"""USER BROWSING CUE:
Cue Type: {cue_type}
Search Query: {query}
Product Name: {product_name}
Price: ₹{price}
Dwell Time: {dwell_seconds} seconds

Select the best intervention lever for this shopper intent and return JSON."""

    payload = {
        "model": config.BROWSING_AGENT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
        "max_tokens": 400,
    }

    url = f"{config.GROQ_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    try:
        req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            result["status"] = "success"
            result["agent_used"] = "BrowsingIntentAgent (Groq)"
            return result
    except Exception as e:
        print(f"[BrowsingIntentAgent] API call failed ({e}), using deterministic fallback")
        return _fallback_recommendation(cue)


def _fallback_recommendation(cue: Dict[str, Any]) -> Dict[str, Any]:
    cue_type = cue.get("type", "product_view")
    query = cue.get("query", "")
    price = cue.get("price", 0)

    if cue_type == "search" and query:
        return {
            "status": "success",
            "recommended_lever_id": "review_summary_surface",
            "headline": f"AI Review & Feature Summary for '{query}'",
            "rationale": f"See top buyer feedback and specs comparing items for {query}.",
            "action_label": "Read AI Summary",
            "action_type": "open_reviews",
            "confidence": "high",
            "agent_used": "BrowsingIntentAgent (Fallback)",
        }
    elif price >= 5000:
        return {
            "status": "success",
            "recommended_lever_id": "emi_plan_highlight",
            "headline": "Split into Easy No-Cost EMIs",
            "rationale": "Qualifies for 0% interest No-Cost EMI starting from ₹1,856/month.",
            "action_label": "Explore EMI Plans",
            "action_type": "scroll_to_emi",
            "confidence": "high",
            "agent_used": "BrowsingIntentAgent (Fallback)",
        }
    else:
        return {
            "status": "success",
            "recommended_lever_id": "free_delivery_waiver",
            "headline": "Express Free Delivery Session Perk",
            "rationale": "Get guaranteed free express delivery by tomorrow 5 PM.",
            "action_label": "Apply Free Delivery",
            "action_type": "open_delivery",
            "confidence": "high",
            "agent_used": "BrowsingIntentAgent (Fallback)",
        }
