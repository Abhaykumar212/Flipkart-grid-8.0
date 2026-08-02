from hashlib import sha256


def assignment_bucket(session_id: str, experiment_id: str) -> int:
    digest = sha256(f"{session_id}:{experiment_id}".encode()).hexdigest()
    return int(digest[:8], 16) % 100


def assign_group(
    session_id: str,
    experiment_id: str,
    *,
    traffic_split: int = 50,
    control_group: str = "CONTROL",
    treatment_group: str = "PERSONALIZED_V1",
) -> str:
    if not 0 <= traffic_split <= 100:
        raise ValueError("traffic_split must be between 0 and 100")
    return (
        treatment_group
        if assignment_bucket(session_id, experiment_id) < traffic_split
        else control_group
    )
