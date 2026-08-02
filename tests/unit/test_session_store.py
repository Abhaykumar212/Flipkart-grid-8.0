import pytest

from backend.storage.session_store import InMemorySessionStore, RedisSessionStore


def test_in_memory_store_uses_defensive_copies_and_caps_lists():
    store = InMemorySessionStore()
    original = {"events": [1]}
    store.set("session:s1:state", original, 60)
    original["events"].append(2)

    stored = store.get("session:s1:state")
    assert stored == {"events": [1]}
    stored["events"].append(3)
    assert store.get("session:s1:state") == {"events": [1]}

    for value in range(55):
        store.append("session:s1:events", value, 60, max_items=50)
    assert store.get("session:s1:events") == list(range(5, 55))


def test_store_rejects_invalid_ttl_and_redis_stub_is_explicit():
    store = InMemorySessionStore()
    with pytest.raises(ValueError):
        store.set("key", "value", 0)
    with pytest.raises(NotImplementedError):
        RedisSessionStore()
