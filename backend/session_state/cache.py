from collections.abc import Iterable

from backend import config
from backend.storage.session_store import SessionStore

from .state import SessionState


def cache_session_state(
    store: SessionStore,
    state: SessionState,
    *,
    event_ids: Iterable[str] = (),
) -> None:
    short_ttl = config.SESSION_TTL_MINUTES * 60
    long_ttl = config.SESSION_HARD_TTL_HOURS * 60 * 60
    dedupe_ttl = config.EVENT_DEDUPE_TTL_HOURS * 60 * 60
    prefix = f"session:{state.session_id}"

    store.set(f"{prefix}:state", state, short_ttl)
    store.set(f"{prefix}:events", state.recent_events, short_ttl)
    store.set(f"{prefix}:counters", state.counters, short_ttl)
    store.set(
        f"{prefix}:interventions",
        state.interventions["shown"],
        long_ttl,
        sliding=False,
        hard_ttl_seconds=long_ttl,
    )

    if state.last_decision is not None:
        store.set(f"{prefix}:last_decision", state.last_decision, short_ttl)
    if state.experiment is not None:
        store.set(
            f"{prefix}:experiment",
            state.experiment,
            long_ttl,
            sliding=False,
            hard_ttl_seconds=long_ttl,
        )

    for event_id in event_ids:
        store.set(
            f"dedupe:event:{event_id}",
            1,
            dedupe_ttl,
            sliding=False,
            hard_ttl_seconds=dedupe_ttl,
        )
