"""Contract tests for the legacy root-cause agent and its trigger policy."""

import pytest

from backend import config
from backend.agents import gate, root_cause
from backend.agents.levers import LEVER_CATALOG, LEVER_IDS, ROOT_CAUSE_CATEGORIES
from backend.schemas import CartContext, CartLine, RootCauseAnalysis
from backend.trace import Stage, Status, TraceRecorder


def sample_features(**overrides):
    base = {
        "seconds_spent_in_cart": 420.0,
        "times_returned_to_product_page": 4,
        "product_reviews_read": 5,
        "seconds_idle_before_checkout": 180.0,
        "delivery_pincode_checks": 3,
        "saved_items_in_wishlist": 2,
        "cart_value_vs_typical_order": 4.9,
        "delivery_fee_percent_of_cart": 9.0,
        "price_dropped_since_first_view": 0,
        "discount_seeking_tendency": 0.85,
        "failed_coupon_attempts": 3,
        "estimated_delivery_days": 8,
        "payment_method_on_file": 0,
        "checkout_steps_completed": 0,
        "payment_attempts_failed": 0,
        "is_guest_checkout": 1,
        "past_abandonment_rate": 0.72,
        "past_order_return_rate": 0.15,
        "lifetime_orders_placed": 2,
        "days_since_last_purchase": 210.0,
        "is_mobile_session": 1,
        "is_late_night_session": 1,
    }
    base.update(overrides)
    return base


def valid_analysis_dict():
    return {
        "primary_root_cause": {
            "category": "cost_friction",
            "headline": "Delivery fee pushes an already-large basket over the line",
            "explanation": "The cart is 4.9x this shopper's usual order and carries a 9% delivery fee.",
            "supporting_evidence": [
                {
                    "signal": "extra_cost_burden_score",
                    "observed_value": "9% fee on a 4.9x basket",
                    "shap_contribution": 1.02,
                    "why_it_matters": "Compounded cost is the dominant driver.",
                }
            ],
        },
        "contributing_factors": [
            {
                "category": "checkout_friction",
                "headline": "No checkout steps completed",
                "signal": "checkout_steps_completed",
            }
        ],
        "shopper_narrative": "The shopper is hesitating over an unusually expensive basket.",
        "confidence": "high",
        "confidence_reasoning": "Evidence concentrates on a single cost driver.",
        "recommended_levers": [
            {
                "lever_id": "free_delivery_waiver",
                "rationale": "Removes the fee that dominates the attribution.",
                "expected_effect": "Directly lowers the cost barrier.",
                "priority": 1,
            }
        ],
        "levers_to_avoid": [
            {"lever_id": "price_drop_alert", "reason": "No price drop has occurred."}
        ],
    }


@pytest.fixture
def gate_store():
    return gate.GateStore()


@pytest.fixture
def evidence_context():
    features = sample_features()
    impacts = {
        "cart_value_vs_typical_order": 0.99,
        "delivery_fee_percent_of_cart": 0.62,
        "checkout_steps_completed": 0.55,
        "payment_method_on_file": -0.40,
        "estimated_delivery_days": 0.31,
    }
    cart = CartContext(
        lines=[
            CartLine(
                product_id="p-1001",
                title="Apple iPhone 16",
                brand="Apple",
                quantity=1,
                selling_price=71999,
                mrp=79900,
                discount_percent=10,
                estimated_delivery_days=8,
            )
        ],
        cart_total=71999,
        mrp_total=79900,
        delivery_fee=6480,
        cart_age_seconds=420,
    )
    return features, impacts, cart


def test_gate_fires_at_or_above_threshold(gate_store):
    result = gate.evaluate(0.94, 400, "sig-a", "s1", gate_store)
    assert result.fired
    assert result.threshold == config.RCA_PROBABILITY_THRESHOLD


def test_gate_does_not_fire_below_threshold(gate_store):
    result = gate.evaluate(0.79, 400, "sig-a", "s1", gate_store)
    assert not result.fired
    assert "below" in result.reason


def test_gate_exact_threshold_boundary_fires(gate_store):
    result = gate.evaluate(config.RCA_PROBABILITY_THRESHOLD, 400, "sig-a", "s1", gate_store)
    assert result.fired


def test_gate_waits_for_cart_warmup(gate_store):
    result = gate.evaluate(0.95, 3, "sig-a", "s1", gate_store)
    assert not result.fired
    assert "old" in result.reason


def test_gate_identical_signature_within_cooldown_is_suppressed(gate_store):
    gate_store.record_run("s1", "sig-a", at=1000.0)
    result = gate.evaluate(0.95, 400, "sig-a", "s1", gate_store, now=1010.0)
    assert not result.fired
    assert "unchanged" in result.reason


def test_gate_changed_signature_refires_immediately(gate_store):
    gate_store.record_run("s1", "sig-a", at=1000.0)
    result = gate.evaluate(0.95, 400, "sig-DIFFERENT", "s1", gate_store, now=1010.0)
    assert result.fired
    assert "changed" in result.reason


def test_gate_cooldown_expiry_allows_refire(gate_store):
    gate_store.record_run("s1", "sig-a", at=1000.0)
    later = 1000.0 + config.RCA_COOLDOWN_SECONDS + 1
    assert gate.evaluate(0.95, 400, "sig-a", "s1", gate_store, now=later).fired


def test_gate_session_budget_is_enforced(gate_store):
    for _ in range(config.RCA_MAX_PER_SESSION):
        gate_store.record_run("s1", "sig-x")
    result = gate.evaluate(0.99, 400, "sig-new", "s1", gate_store)
    assert not result.fired
    assert "budget" in result.reason


def test_gate_force_bypasses_cooldown_but_not_budget(gate_store):
    gate_store.record_run("s1", "sig-a", at=1000.0)
    assert gate.evaluate(
        0.95, 400, "sig-a", "s1", gate_store, force=True, now=1001.0
    ).fired

    for _ in range(config.RCA_MAX_PER_SESSION):
        gate_store.record_run("s2", "sig-a")
    capped = gate.evaluate(0.95, 400, "sig-a", "s2", gate_store, force=True)
    assert not capped.fired, "force must not bypass the hard session cap"


def test_gate_force_ignores_low_probability(gate_store):
    assert gate.evaluate(0.05, 400, "sig-a", "s1", gate_store, force=True).fired


def test_gate_sessions_are_isolated(gate_store):
    gate_store.record_run("s1", "sig-a", at=1000.0)
    assert gate.evaluate(0.95, 400, "sig-a", "s2", gate_store, now=1001.0).fired


def test_feature_signature_is_stable():
    assert root_cause.build_feature_signature(sample_features()) == root_cause.build_feature_signature(sample_features())


def test_material_change_alters_feature_signature():
    base = root_cause.build_feature_signature(sample_features())
    changed = root_cause.build_feature_signature(sample_features(payment_attempts_failed=3))
    assert base != changed


def test_immaterial_drift_does_not_alter_feature_signature():
    base = root_cause.build_feature_signature(sample_features())
    drifted = root_cause.build_feature_signature(
        sample_features(seconds_spent_in_cart=431.0, seconds_idle_before_checkout=194.0)
    )
    assert base == drifted


def test_evidence_is_ranked_by_absolute_shap(evidence_context):
    features, impacts, _ = evidence_context
    evidence = root_cause.build_evidence(features, impacts)
    magnitudes = [abs(item["shap_contribution"]) for item in evidence]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_evidence_includes_protective_signals(evidence_context):
    features, impacts, _ = evidence_context
    directions = {item["direction"] for item in root_cause.build_evidence(features, impacts)}
    assert "reduces abandonment risk" in directions


def test_evidence_carries_human_labels_and_values(evidence_context):
    features, impacts, _ = evidence_context
    top = root_cause.build_evidence(features, impacts)[0]
    assert top["signal"] == "cart_value_vs_typical_order"
    assert "4.90x" in top["observed_value"]
    assert top["label"] != top["signal"]


def test_prompt_contains_grounding(evidence_context):
    features, impacts, cart = evidence_context
    evidence = root_cause.build_evidence(features, impacts)
    prompt = root_cause.build_prompt(0.94, "high", 0.88, features, evidence, cart)

    assert "SHAP ATTRIBUTION" in prompt
    assert "cart_value_vs_typical_order" in prompt
    assert "Apple iPhone 16" in prompt
    assert "free_delivery_waiver" in prompt
    for category in ROOT_CAUSE_CATEGORIES:
        assert category in prompt


def test_prompt_never_contains_api_key(evidence_context):
    features, impacts, cart = evidence_context
    prompt = root_cause.build_prompt(
        0.94, "high", 0.88, features, root_cause.build_evidence(features, impacts), cart
    )
    assert "gsk_" not in prompt


def test_valid_response_payload_parses():
    analysis = RootCauseAnalysis.model_validate(valid_analysis_dict())
    assert analysis.primary_root_cause.category == "cost_friction"
    assert analysis.recommended_levers[0].lever_id == "free_delivery_waiver"


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("recommended_levers", 0, "lever_id"), "send_carrier_pigeon"),
        (("primary_root_cause", "category"), "vibes"),
    ),
)
def test_unknown_response_enums_are_rejected(path, value):
    payload = valid_analysis_dict()
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    with pytest.raises(Exception):
        RootCauseAnalysis.model_validate(payload)


def test_missing_required_response_section_is_rejected():
    payload = valid_analysis_dict()
    del payload["shopper_narrative"]
    with pytest.raises(Exception):
        RootCauseAnalysis.model_validate(payload)


def test_groq_schema_is_strict_everywhere():
    def assert_strict(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, (
                    f"object missing additionalProperties:false: {list(node.get('properties', {}))}"
                )
            for value in node.values():
                assert_strict(value)
        elif isinstance(node, list):
            for value in node:
                assert_strict(value)

    assert_strict(root_cause._response_schema())


def test_schema_enums_match_catalog():
    schema = root_cause._response_schema()
    lever_enum = schema["properties"]["recommended_levers"]["items"]["properties"]["lever_id"]["enum"]
    assert set(lever_enum) == set(LEVER_IDS)


def test_every_lever_addresses_a_known_category():
    for lever_id, meta in LEVER_CATALOG.items():
        for category in meta["addresses"]:
            assert category in ROOT_CAUSE_CATEGORIES, f"{lever_id} -> {category}"


def test_every_category_has_at_least_one_lever():
    covered = {category for meta in LEVER_CATALOG.values() for category in meta["addresses"]}
    for category in ROOT_CAUSE_CATEGORIES:
        assert category in covered, f"no lever addresses {category}"


def test_trace_span_records_duration_and_detail():
    recorder = TraceRecorder()
    with recorder.span(Stage.MODEL_INFERENCE, "test") as span:
        span["detail"] = {"probability": 0.9}
    assert len(recorder.spans) == 1
    assert recorder.spans[0]["status"] == Status.OK
    assert recorder.spans[0]["detail"]["probability"] == 0.9
    assert recorder.spans[0]["source"] == "backend"


def test_trace_span_marks_error_and_reraises():
    recorder = TraceRecorder()
    with pytest.raises(ValueError):
        with recorder.span(Stage.ROOT_CAUSE_AGENT, "boom"):
            raise ValueError("kaboom")
    assert recorder.spans[0]["status"] == Status.ERROR
    assert "kaboom" in recorder.spans[0]["detail"]["error"]


def test_trace_run_ids_are_unique():
    assert TraceRecorder().run_id != TraceRecorder().run_id


def test_redacted_key_hint_never_exposes_key():
    hint = config.redacted_key_hint()
    if config.GROQ_API_KEY:
        assert config.GROQ_API_KEY not in hint
        assert "…" in hint
    else:
        assert hint == "not-set"


def test_token_budget_is_high_enough_for_schema():
    assert config.RCA_MAX_TOKENS >= 1500


def test_threshold_matches_high_risk_tier():
    from backend.main import _risk_tier

    assert _risk_tier(config.RCA_PROBABILITY_THRESHOLD) == "high"
