"""Guards on the prose a judge actually reads.

The explanation trail is the project's most-judged surface, so these tests
assert the two failure modes that destroy it: a raw feature identifier reaching
the page, and a probability rendered as an unearned certainty.
"""

import re

import pytest

from backend.explainability.i18n import hindi_feature_statement, localized_template
from backend.explainability.narratives import (
    NARRATIVES,
    display_probability_pct,
    duration_phrase,
    informative,
    statement,
)
from backend.feature_engine.schema import FEATURE_BY_NAME, FEATURE_NAMES

IDENTIFIER = re.compile(r"\b(?:u|c|p|d|pay|s|x|i)_[a-z_]+\b")


def test_every_served_feature_has_a_narrative():
    assert set(NARRATIVES) == set(FEATURE_NAMES)


@pytest.mark.parametrize("feature", FEATURE_NAMES)
def test_no_statement_leaks_a_feature_identifier(feature):
    spec = FEATURE_BY_NAME[feature]
    for value in (spec.minimum, spec.default, spec.maximum):
        for rendered in (statement(feature, value), hindi_feature_statement(feature, value)):
            assert not IDENTIFIER.search(rendered), rendered
            assert rendered.endswith((".", "।")), rendered


@pytest.mark.parametrize("feature", FEATURE_NAMES)
def test_no_statement_prints_raw_float_noise(feature):
    spec = FEATURE_BY_NAME[feature]
    rendered = statement(feature, (spec.minimum + spec.maximum) / 3 + 0.123456)
    assert not re.search(r"\d\.\d{3,}", rendered), rendered


def test_zero_valued_behaviour_is_not_treated_as_evidence():
    assert not informative("s_review_open_count", 0.0)
    assert informative("s_review_open_count", 3.0)


def test_zero_is_evidence_when_the_absence_is_the_point():
    # No saved card is exactly what explains a stalled checkout.
    assert informative("pay_method_on_file", 0.0)
    assert "no saved payment method" in statement("pay_method_on_file", 0.0)


def test_durations_read_as_a_person_would_say_them():
    assert duration_phrase(0.0095) == "under a second"
    assert duration_phrase(45) == "45 seconds"
    assert duration_phrase(120) == "2 minutes"
    assert duration_phrase(7200) == "2.0 hours"


def test_probability_never_renders_as_certainty():
    assert display_probability_pct(0.99928) == 99
    assert display_probability_pct(1.0) == 99
    assert display_probability_pct(0.0) == 1
    assert display_probability_pct(0.723) == 72


def test_rendered_trail_stays_identifier_free_in_both_languages():
    explanation = {
        "observations": [
            {"feature": "s_review_open_count", "value": 3.0, "statement": statement("s_review_open_count", 3.0)},
            {"feature": "s_checkout_start_count", "value": 0.0, "statement": statement("s_checkout_start_count", 0.0)},
        ],
        "risk": {"probability": 0.9993, "band": "HIGH", "statement": "Abandonment risk is high at 99%."},
        "inference": {"root_cause": "PRODUCT_QUALITY_UNCERTAINTY", "statement": "Repeated review visits."},
        "action": {"decision": "INTERVENE", "intervention": "REVIEW_SUMMARY", "statement": "Review summary."},
    }
    for language in ("en", "hi"):
        rendered = localized_template(explanation, language)
        assert not IDENTIFIER.search(rendered), rendered
        assert "100%" not in rendered
