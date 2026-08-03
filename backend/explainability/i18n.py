from __future__ import annotations

from typing import Any


SUPPORTED_LANGUAGES = {"en", "hi"}

HINDI_FEATURE_TEMPLATES = {
    "s_review_open_count": "ग्राहक ने समीक्षाएँ {value:g} बार दोबारा खोलीं।",
    "s_review_dwell_seconds": "ग्राहक ने समीक्षाएँ पढ़ने में {value:g} सेकंड बिताए।",
    "s_similar_product_view_count": "ग्राहक ने {value:g} समान उत्पाद देखे।",
    "s_price_sort_count": "ग्राहक ने कीमत के अनुसार {value:g} बार क्रमबद्ध किया।",
    "s_coupon_search_count": "ग्राहक ने कूपन के लिए {value:g} बार खोज की।",
    "d_check_count": "ग्राहक ने डिलीवरी {value:g} बार जाँची।",
    "pay_failure_count": "चेकआउट में {value:g} भुगतान प्रयास विफल हुए।",
    "pay_method_change_count": "भुगतान विधि {value:g} बार बदली गई।",
    "s_idle_seconds_current": "सत्र {value:g} सेकंड से निष्क्रिय है।",
    "c_value": "कार्ट का मूल्य ₹{value:,.0f} है।",
}


def resolve_language(accept_language: str | None) -> str:
    """Resolve an Accept-Language value to a supported two-letter language."""

    if not accept_language:
        return "en"
    for item in accept_language.split(","):
        tag = item.split(";", 1)[0].strip().lower().split("-", 1)[0]
        if tag in SUPPORTED_LANGUAGES:
            return tag
    return "en"


def _english(explanation: dict[str, Any]) -> str:
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


def _hindi(explanation: dict[str, Any]) -> str:
    observations: list[str] = []
    for item in explanation.get("observations", [])[:2]:
        if not isinstance(item, dict):
            continue
        feature = str(item.get("feature", ""))
        value = float(item.get("value", 0.0))
        template = HINDI_FEATURE_TEMPLATES.get(
            feature,
            "{feature} संकेत का मान {value:g} है।",
        )
        observations.append(template.format(feature=feature, value=value))
    risk = explanation.get("risk", {})
    inference = explanation.get("inference", {})
    action = explanation.get("action", {})
    probability = round(float(risk.get("probability", 0.0)) * 100)
    return " ".join([
        *observations,
        f"कार्ट छोड़ने का जोखिम {risk.get('band', 'UNKNOWN')} है: {probability}%।",
        f"प्रमुख कारण {inference.get('root_cause', 'UNKNOWN')} है।",
        f"निर्णय {action.get('decision', 'NO_ACTION')} है और हस्तक्षेप "
        f"{action.get('intervention', 'NO_ACTION')} है।",
    ]).strip()


def localized_template(explanation: dict[str, Any], language: str) -> str:
    return _hindi(explanation) if language == "hi" else _english(explanation)
