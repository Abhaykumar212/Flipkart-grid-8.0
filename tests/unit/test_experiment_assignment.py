from backend.experimentation.assign import assign_group, assignment_bucket


def test_assignment_is_deterministic_and_close_to_even_split() -> None:
    first = [assign_group(f"session-{index}", "EXP-001") for index in range(10_000)]
    second = [assign_group(f"session-{index}", "EXP-001") for index in range(10_000)]
    assert first == second
    treatment = first.count("PERSONALIZED_V1")
    assert 4_800 <= treatment <= 5_200


def test_bucket_is_replay_stable() -> None:
    assert assignment_bucket("scenario-h-control", "EXP-001") == assignment_bucket("scenario-h-control", "EXP-001")
