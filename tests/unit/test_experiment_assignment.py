from backend.experimentation.assign import assign_group, assignment_bucket


def test_assignment_is_deterministic_and_close_to_even_split() -> None:
    # The split is pinned rather than taken from config: what is under test is
    # that the bucket hash spreads evenly, not whatever percentage the product
    # currently happens to be rolled out at.
    first = [assign_group(f"s-{i}", "EXP-001", traffic_split=50) for i in range(10_000)]
    second = [assign_group(f"s-{i}", "EXP-001", traffic_split=50) for i in range(10_000)]
    assert first == second
    treatment = first.count("PERSONALIZED_V1")
    assert 4_800 <= treatment <= 5_200


def test_assignment_honours_the_configured_split() -> None:
    treatment = [
        assign_group(f"s-{i}", "EXP-001", traffic_split=80) for i in range(10_000)
    ].count("PERSONALIZED_V1")
    assert 7_800 <= treatment <= 8_200


def test_bucket_is_replay_stable() -> None:
    assert assignment_bucket("scenario-h-control", "EXP-001") == assignment_bucket("scenario-h-control", "EXP-001")
