"""Re-engagement agent: LLM-powered session analysis and email generation.

Analyses a shopper's full behavioral timeline after session abandonment and
generates a hyper-personalized HTML re-engagement email addressing the exact
concerns and interests the shopper demonstrated during their visit.

Uses Groq's chat-completions endpoint (same infrastructure as root_cause.py)
with the llama-3.3-70b-versatile model for free-form text generation.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .. import config


# ---------------------------------------------------------------------------
# Groq API helper — free-form text (no strict JSON schema needed)
# ---------------------------------------------------------------------------

REENGAGEMENT_MODEL = os.getenv("REENGAGEMENT_MODEL", "llama-3.3-70b-versatile")
REENGAGEMENT_MAX_TOKENS = int(os.getenv("REENGAGEMENT_MAX_TOKENS", "4096"))
REENGAGEMENT_TEMPERATURE = float(os.getenv("REENGAGEMENT_TEMPERATURE", "0.4"))


def _call_groq(system_prompt: str, user_prompt: str) -> str:
    """Fire a single Groq chat-completion and return the assistant message."""
    body = json.dumps({
        "model": REENGAGEMENT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": REENGAGEMENT_TEMPERATURE,
        "max_tokens": REENGAGEMENT_MAX_TOKENS,
    }).encode("utf-8")

    api_key = config.REENGAGEMENT_GROQ_API_KEY or config.GROQ_API_KEY
    request = urllib.request.Request(
        f"{config.GROQ_BASE_URL}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "flipkart-grid-reengagement/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
            return payload["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            detail = json.loads(error.read()).get("error", {}).get("message", "")
        except Exception:
            pass
        raise RuntimeError(f"Groq HTTP {error.code}: {detail}") from error


# ---------------------------------------------------------------------------
# Step 1: Journey Analysis
# ---------------------------------------------------------------------------

_ANALYSIS_SYSTEM = """\
You are an expert e-commerce behavioral psychologist and data analyst working \
for Flipkart. Your job is to analyse a shopper's complete session timeline and \
extract actionable insights.

Given a timestamped event log from a shopping session, produce a structured \
analysis with EXACTLY these two sections:

SUMMARY:
Write a 3-5 sentence narrative of the shopper's journey. Mention:
- What they searched for
- Which products they viewed and for how long
- Whether they compared products
- What they added to cart
- Where exactly they dropped off (which page, which step)
- Total session duration

SIGNALS:
List every behavioral signal you detect, each on its own line with a label. \
For example:
- REVIEW_FOCUSED: Spent 3+ minutes reading reviews for MacBook Pro M4
- PRICE_SENSITIVE: Compared prices across 3 similar laptops
- COMPARISON_SHOPPER: Actively compared MacBook Pro M4 vs Dell XPS 15
- CHECKOUT_FRICTION: Reached payment step but abandoned
- HIGH_INTENT: Added item to cart, spent significant time on product page
- BRAND_LOYAL: Only viewed Apple products
- DELIVERY_CONCERNED: Checked delivery pincode multiple times

Be specific with product names, durations, and prices. Do NOT make up data \
that isn't in the timeline."""


def analyse_journey(
    timeline_events: List[Dict[str, Any]],
    product_catalog: Dict[str, Any],
) -> Dict[str, str]:
    """Summarise the session and extract behavioral signals via LLM."""
    events_text = json.dumps(timeline_events, indent=2, default=str)
    catalog_text = json.dumps(product_catalog, indent=2, default=str)

    prompt = (
        f"## Session Timeline ({len(timeline_events)} events)\n\n"
        f"{events_text}\n\n"
        f"## Product Catalog Context\n\n"
        f"{catalog_text}\n\n"
        "Analyse this session and provide the SUMMARY and SIGNALS sections."
    )

    response = _call_groq(_ANALYSIS_SYSTEM, prompt)

    # Parse into sections
    summary = response
    signals = ""
    if "SIGNALS:" in response:
        parts = response.split("SIGNALS:", 1)
        summary = parts[0].replace("SUMMARY:", "").strip()
        signals = parts[1].strip()
    elif "SUMMARY:" in response:
        summary = response.split("SUMMARY:", 1)[1].strip()

    return {"summary": summary, "signals": signals}


# ---------------------------------------------------------------------------
# Step 2: Email Generation
# ---------------------------------------------------------------------------

_EMAIL_SYSTEM = """\
You are an expert email marketer for Flipkart, India's largest e-commerce \
platform. Generate a highly personalized, conversion-optimised HTML \
re-engagement email based on a shopper's behavioral analysis.

RULES:
1. The email MUST be deeply personalized to the shopper's exact journey — \
   reference the specific products they viewed, the time they spent, and \
   their behavioral signals.
2. Structure the email based on what signals are present:
   - If COMPARISON_SHOPPER: Include a clean comparison table of the products
   - If REVIEW_FOCUSED: Quote 1-2 top positive reviews they might have seen
   - If PRICE_SENSITIVE: Emphasize value, mention any price drops or deals
   - If HIGH_INTENT (cart but no checkout): Create urgency ("Your cart is waiting")
   - If CHECKOUT_FRICTION: Address trust concerns (secure payment, easy returns)
   - If DELIVERY_CONCERNED: Highlight delivery guarantees
3. Include a prominent CTA button linking back to the product/cart
4. Use Flipkart's brand colors: primary blue #2874F0, accent yellow #FFE11B
5. Keep the tone friendly, helpful, not pushy
6. The HTML should be email-safe (inline styles, no external CSS, table layout)

OUTPUT FORMAT:
Return ONLY valid JSON with exactly two keys:
{
  "subject": "...",
  "html_body": "..."
}

The subject line should be compelling and personal (use the product name).
The html_body should be a complete, self-contained HTML email body wrapped \
in a single <div> element with inline styles. Use tables for layout.

Do NOT wrap the JSON in markdown code fences. Return raw JSON only."""


def generate_reengagement_email(
    journey_analysis: Dict[str, str],
    user_email: str,
    product_catalog: Dict[str, Any],
) -> Tuple[str, str]:
    """Generate a personalized HTML re-engagement email."""
    analysis_text = json.dumps(journey_analysis, indent=2)
    catalog_text = json.dumps(product_catalog, indent=2, default=str)

    prompt = (
        f"## Journey Analysis\n\n{analysis_text}\n\n"
        f"## Product Catalog\n\n{catalog_text}\n\n"
        f"## Recipient\n{user_email}\n\n"
        "Generate the personalized re-engagement email JSON now."
    )

    response = _call_groq(_EMAIL_SYSTEM, prompt)

    # Strip any markdown fencing the model might have added
    cleaned = response.strip()
    if cleaned.startswith("```"):
        # Remove first line and last line
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(cleaned)
        subject = data.get("subject", "Your cart is waiting for you!")
        html_body = data.get("html_body", _fallback_email_html(journey_analysis))
        return subject, html_body
    except json.JSONDecodeError as e:
        print(f"[REENGAGEMENT] JSON parse failed ({e}), using response as body")
        return "We saved your favourites for you!", _fallback_email_html(
            journey_analysis, raw_response=cleaned
        )


def _fallback_email_html(
    analysis: Dict[str, str], raw_response: str = ""
) -> str:
    """Minimal fallback email when the LLM doesn't produce valid JSON."""
    summary = analysis.get("summary", "")
    return f"""\
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: #2874F0; padding: 20px; text-align: center; border-radius: 4px 4px 0 0;">
    <h1 style="color: #fff; margin: 0; font-size: 24px;">Flipkart</h1>
  </div>
  <div style="background: #fff; padding: 24px; border: 1px solid #e0e0e0;">
    <h2 style="color: #212121; margin-top: 0;">We noticed you left something behind</h2>
    <p style="color: #666; line-height: 1.6;">{summary}</p>
    <div style="text-align: center; margin: 24px 0;">
      <a href="http://localhost:5173" style="background: #FB641B; color: #fff; \
padding: 12px 32px; text-decoration: none; border-radius: 2px; font-weight: bold; \
display: inline-block;">Continue Shopping</a>
    </div>
  </div>
  <div style="text-align: center; padding: 16px; color: #999; font-size: 12px;">
    Flipkart GRiD 8.0 — AI-powered re-engagement
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def run_reengagement_pipeline(
    session_id: str,
    timeline_events: List[Dict[str, Any]],
    user_email: str,
    product_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Run the complete re-engagement pipeline: analyse → generate email.

    Returns a dict with subject, html_body, analysis_summary, signals, and
    status ('generated' on success, empty dict on failure).
    """
    start = time.time()
    try:
        # Step 1: Analyse the journey
        analysis = analyse_journey(timeline_events, product_catalog)

        # Step 2: Generate personalized email
        subject, html_body = generate_reengagement_email(
            analysis, user_email, product_catalog
        )

        latency_ms = round((time.time() - start) * 1000, 1)
        print(
            f"[REENGAGEMENT] Pipeline complete for {session_id} "
            f"({latency_ms}ms, model={REENGAGEMENT_MODEL})"
        )

        return {
            "session_id": session_id,
            "email_to": user_email,
            "subject": subject,
            "body_html": html_body,
            "analysis_summary": analysis["summary"],
            "behavioral_signals": analysis["signals"],
            "status": "generated",
            "latency_ms": latency_ms,
            "model_used": REENGAGEMENT_MODEL,
        }
    except Exception as e:
        latency_ms = round((time.time() - start) * 1000, 1)
        print(f"[REENGAGEMENT] Pipeline failed for {session_id}: {e} ({latency_ms}ms)")
        return {
            "session_id": session_id,
            "status": "error",
            "error": str(e),
            "latency_ms": latency_ms,
        }
