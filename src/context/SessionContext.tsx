import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ApiError, apiPost } from "../lib/api";
import {
  eventClient,
  type EventEnvelope,
  type EventInput,
  type EventType,
} from "../lib/events";

const SESSION_ID_KEY = "fk-session-id-v1";
const SESSION_STARTED_PREFIX = "fk-session-started:";
const SESSION_ENDED_PREFIX = "fk-session-ended:";

interface SessionIdentity {
  sessionId: string;
}

interface SessionContextValue {
  sessionId: string;
  emit: <T extends EventType>(eventType: T, input: EventInput<T>) => EventEnvelope | null;
}

const SessionContext = createContext<SessionContextValue | null>(null);

function safeGet(key: string): string | null {
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    window.sessionStorage.setItem(key, value);
  } catch {
    // The in-memory session remains usable when browser storage is blocked.
  }
}

function createIdentity(): SessionIdentity {
  const existing = safeGet(SESSION_ID_KEY);
  if (existing && !safeGet(`${SESSION_ENDED_PREFIX}${existing}`)) {
    return { sessionId: existing };
  }
  const sessionId = `S-${crypto.randomUUID()}`;
  safeSet(SESSION_ID_KEY, sessionId);
  return { sessionId };
}

function initializeSession(): SessionIdentity {
  const identity = createIdentity();
  eventClient.pause();
  eventClient.setSession(identity.sessionId);
  const startedKey = `${SESSION_STARTED_PREFIX}${identity.sessionId}`;
  if (!safeGet(startedKey)) {
    safeSet(startedKey, "1");
    eventClient.emit("SESSION_STARTED", {
      metadata: {
        device_type: window.innerWidth < 768 ? "MOBILE" : "DESKTOP",
        referral_source: document.referrer ? "REFERRAL" : "DIRECT",
        viewport_width: Math.max(1, window.innerWidth),
      },
    });
  }
  return identity;
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [identity] = useState(initializeSession);
  const creationRequest = useRef<Promise<unknown> | null>(null);

  useEffect(() => {
    if (creationRequest.current === null) {
      creationRequest.current = apiPost<{ session_id: string }>("/api/v1/sessions", {
        session_id: identity.sessionId,
        device_type: window.innerWidth < 768 ? "MOBILE" : "DESKTOP",
        referral_source: document.referrer ? "REFERRAL" : "DIRECT",
      }).catch((error: unknown) => {
        // The queued SESSION_STARTED event can create the row after an outage.
        if (error instanceof ApiError && error.status === 409) return;
      });
    }
    void creationRequest.current.finally(() => eventClient.resume());

    const endSession = (event: PageTransitionEvent) => {
      if (event.persisted) return;
      eventClient.resume();
      safeSet(`${SESSION_ENDED_PREFIX}${identity.sessionId}`, "1");
      eventClient.emit("SESSION_ENDED", { metadata: { reason: "UNLOAD" } });
      eventClient.flushWithBeacon();
    };
    window.addEventListener("pagehide", endSession);
    return () => window.removeEventListener("pagehide", endSession);
  }, [identity]);

  const value = useMemo<SessionContextValue>(() => ({
    sessionId: identity.sessionId,
    emit: (eventType, input) => eventClient.emit(eventType, input),
  }), [identity.sessionId]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used within SessionProvider");
  return context;
}
