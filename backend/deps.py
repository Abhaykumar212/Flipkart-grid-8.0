from backend.storage.session_store import InMemorySessionStore, SessionStore

session_store = InMemorySessionStore()


def get_session_store() -> SessionStore:
    return session_store
