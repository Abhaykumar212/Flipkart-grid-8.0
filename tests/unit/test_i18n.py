from backend.explainability.i18n import localized_template, resolve_language


EXPLANATION = {
    "observations": [
        {"feature": "s_review_open_count", "value": 3, "statement": "Reviews opened 3 times."},
    ],
    "risk": {"probability": 0.82, "band": "HIGH", "statement": "Risk is HIGH at 82%."},
    "inference": {
        "root_cause": "PRODUCT_QUALITY_UNCERTAINTY",
        "statement": "Quality uncertainty was detected.",
    },
    "action": {
        "decision": "INTERVENE",
        "intervention": "REVIEW_SUMMARY",
        "statement": "Show the review summary.",
    },
}


def test_accept_language_resolution_and_fallback():
    assert resolve_language("hi-IN,hi;q=0.9,en;q=0.8") == "hi"
    assert resolve_language("fr-FR") == "en"
    assert resolve_language(None) == "en"


def test_hindi_template_preserves_identifiers_and_numbers():
    rendered = localized_template(EXPLANATION, "hi")
    assert "ग्राहक" in rendered
    for token in (
        "3",
        "82",
        "HIGH",
        "PRODUCT_QUALITY_UNCERTAINTY",
        "INTERVENE",
        "REVIEW_SUMMARY",
    ):
        assert token in rendered


def test_unsupported_language_uses_english():
    assert localized_template(EXPLANATION, "fr") == localized_template(EXPLANATION, "en")
