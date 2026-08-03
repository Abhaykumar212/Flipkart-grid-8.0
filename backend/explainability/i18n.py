from __future__ import annotations

from typing import Any

from .narratives import NARRATIVES, display_probability_pct, format_value


SUPPORTED_LANGUAGES = {"en", "hi"}

#: Hindi sentences for the behavioural signals that actually surface as
#: evidence. Anything outside this set falls back to a Hindi noun phrase rather
#: than a raw identifier, so Hindi output holds the same bar as English.
HINDI_FEATURE_TEMPLATES = {
    "s_review_open_count": "ग्राहक ने समीक्षाएँ {value} बार दोबारा खोलीं।",
    "s_review_dwell_seconds": "ग्राहक ने समीक्षाएँ पढ़ने में {value} बिताए।",
    "s_similar_product_view_count": "ग्राहक ने {value} समान उत्पाद देखे।",
    "s_comparison_count": "ग्राहक ने {value} बार उत्पादों की तुलना की।",
    "s_distinct_products_viewed": "ग्राहक ने {value} अलग-अलग उत्पाद देखे।",
    "s_price_sort_count": "ग्राहक ने कीमत के अनुसार {value} बार क्रमबद्ध किया।",
    "s_coupon_search_count": "ग्राहक ने कूपन के लिए {value} बार खोज की।",
    "s_cart_product_switch_count": "ग्राहक ने कार्ट के उत्पाद {value} बार बदले।",
    "s_cart_view_count": "ग्राहक {value} बार कार्ट पर लौटा।",
    "s_back_from_checkout_count": "ग्राहक {value} बार चेकआउट से वापस आया।",
    "s_checkout_start_count": "ग्राहक ने {value} बार चेकआउट शुरू किया।",
    "s_idle_seconds_current": "सत्र {value} से निष्क्रिय है।",
    "s_duration_seconds": "सत्र {value} से चल रहा है।",
    "d_check_count": "ग्राहक ने डिलीवरी {value} बार जाँची।",
    "d_max_days": "सबसे धीमी वस्तु {value} दिनों में पहुँचेगी।",
    "d_fee_pct_of_cart": "डिलीवरी शुल्क कार्ट मूल्य का {value} है।",
    "pay_failure_count": "चेकआउट में {value} भुगतान प्रयास विफल हुए।",
    "pay_method_change_count": "भुगतान विधि {value} बार बदली गई।",
    "pay_method_on_file": "ग्राहक के पास कोई सहेजी गई भुगतान विधि नहीं है।",
    "c_value": "कार्ट का मूल्य {value} है।",
    "c_value_to_aov_ratio": "कार्ट ग्राहक के सामान्य ऑर्डर का {value} है।",
    "c_age_seconds": "कार्ट {value} से खुला है।",
    "c_item_count": "कार्ट में {value} वस्तुएँ हैं।",
    "p_avg_rating": "कार्ट की वस्तुओं की औसत रेटिंग {value} है।",
    "p_any_out_of_stock": "कार्ट की कम से कम एक वस्तु स्टॉक में नहीं है।",
    "u_prior_abandonment_rate": "यह ग्राहक पहले {value} कार्ट छोड़ चुका है।",
    "u_is_new_user": "यह एक बिल्कुल नया ग्राहक है।",
}

#: Short Hindi noun phrases used to keep the generic fallback grammatical.
HINDI_FEATURE_NOUNS = {
    "u": "ग्राहक इतिहास संकेत",
    "c": "कार्ट संकेत",
    "p": "उत्पाद संकेत",
    "d": "डिलीवरी संकेत",
    "pay": "भुगतान संकेत",
    "s": "सत्र संकेत",
    "x": "संदर्भ संकेत",
    "i": "हस्तक्षेप संकेत",
}

HINDI_CAUSE_NAMES = {
    "PRICE_SENSITIVITY": "कीमत के प्रति संवेदनशीलता",
    "PRODUCT_QUALITY_UNCERTAINTY": "उत्पाद गुणवत्ता को लेकर अनिश्चितता",
    "CHOICE_OVERLOAD": "बहुत अधिक विकल्प",
    "DELIVERY_CONCERN": "डिलीवरी की चिंता",
    "AFFORDABILITY_OR_EMI_NEED": "किफ़ायत या EMI की आवश्यकता",
    "CHECKOUT_OR_PAYMENT_FAILURE": "चेकआउट या भुगतान में रुकावट",
    "PRODUCT_AVAILABILITY_CONCERN": "उपलब्धता की चिंता",
    "LOW_PURCHASE_INTENT": "कम खरीद इरादा",
    "TRUST_OR_RETURN_POLICY_CONCERN": "भरोसे या वापसी नीति की चिंता",
    "SESSION_INTERRUPTION_OR_DISTRACTION": "सत्र में बाधा",
    "UNKNOWN": "अज्ञात",
}

HINDI_BANDS = {"HIGH": "उच्च", "MEDIUM": "मध्यम", "LOW": "कम"}


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


def _hindi_duration(seconds: float) -> str:
    """Speak a duration in Hindi. Numerals stay Latin so grounding still holds."""

    if seconds < 1:
        return "एक सेकंड से कम"
    if seconds < 90:
        return f"{seconds:.0f} सेकंड"
    if seconds < 5_400:
        return f"{seconds / 60:.0f} मिनट"
    return f"{seconds / 3_600:.1f} घंटे"


def _hindi_value(value: float, kind: str) -> str:
    return _hindi_duration(value) if kind == "seconds" else format_value(value, kind)


def hindi_feature_statement(feature: str, value: float) -> str:
    """Render one feature reading in Hindi without leaking an identifier."""

    narrative = NARRATIVES.get(feature)
    kind = narrative.kind if narrative else "number"
    if feature == "pay_method_on_file" and value:
        return "ग्राहक के पास सहेजी गई भुगतान विधि है।"
    template = HINDI_FEATURE_TEMPLATES.get(feature)
    if template is not None:
        if "{value}" not in template:
            return template
        return template.format(value=_hindi_value(value, kind))
    noun = HINDI_FEATURE_NOUNS.get(feature.split("_", 1)[0], "संकेत")
    return f"{noun} का मान {_hindi_value(value, kind)} है।"


def _hindi(explanation: dict[str, Any]) -> str:
    observations: list[str] = []
    for item in explanation.get("observations", [])[:2]:
        if not isinstance(item, dict):
            continue
        observations.append(
            hindi_feature_statement(
                str(item.get("feature", "")), float(item.get("value", 0.0))
            )
        )
    risk = explanation.get("risk", {})
    inference = explanation.get("inference", {})
    action = explanation.get("action", {})
    band = str(risk.get("band", "UNKNOWN"))
    probability = display_probability_pct(float(risk.get("probability", 0.0)))
    cause = str(inference.get("root_cause", "UNKNOWN"))
    return " ".join([
        *observations,
        f"कार्ट छोड़ने का जोखिम {HINDI_BANDS.get(band, band)} ({band}) है: {probability}%।",
        f"प्रमुख कारण {HINDI_CAUSE_NAMES.get(cause, cause)} ({cause}) है।",
        f"निर्णय {action.get('decision', 'NO_ACTION')} है और हस्तक्षेप "
        f"{action.get('intervention', 'NO_ACTION')} है।",
    ]).strip()


def localized_template(explanation: dict[str, Any], language: str) -> str:
    return _hindi(explanation) if language == "hi" else _english(explanation)
