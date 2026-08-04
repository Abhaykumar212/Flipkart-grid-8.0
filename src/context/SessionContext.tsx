import {
  createContext,
  useCallback,
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

export interface RecommendedIntervention {
  decision_id?: string;
  type: string;
  display_name?: string;
  channel: "INLINE_CARD" | "ASSISTANT_PANEL" | "BANNER" | "COMPARISON_DRAWER" | "CHECKOUT_PANEL" | null;
  headline?: string;
  body?: string;
  cta_label?: string;
  reason: string;
  confidence: number;
  discount_pct?: number;
  review_product_id?: string | null;
}

export interface DecisionResponse {
  decision_id?: string;
  session_id: string;
  decision?: "INTERVENE" | "NO_ACTION" | "ABSTAIN";
  abandonment_probability?: number;
  risk_level?: "LOW" | "MEDIUM" | "HIGH";
  recommended_intervention?: RecommendedIntervention;
  explanation?: Record<string, unknown>;
  suppressed: boolean;
  suppression_reason?: string;
}

interface SessionContextValue {
  sessionId: string;
  emit: <T extends EventType>(eventType: T, input: EventInput<T>) => EventEnvelope | null;
  latestDecision: DecisionResponse | null;
  requestDecision: (trigger: EventType | "PERIODIC", force?: boolean) => Promise<DecisionResponse | null>;
  clearDecision: (decisionId?: string) => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);
const DECISION_TRIGGER_TYPES = new Set<EventType>([
  "CART_VIEWED",
  "ITEM_ADDED_TO_CART",
  "CHECKOUT_STARTED",
  "PAYMENT_FAILED",
  "PAYMENT_METHOD_CHANGED",
  "DELIVERY_CHECKED",
  "COUPON_SEARCHED",
  "REVIEW_OPENED",
  "SIMILAR_PRODUCT_VIEWED",
  "PRODUCT_COMPARED",
  // Research behaviour, not just cart activity. Must stay in step with
  // THRESHOLD_TRIGGERS in backend/orchestrator/triggers.py — the backend
  // rejects any trigger name this list invents.
  "REVIEW_DWELL_RECORDED",
  "PRODUCT_VIEWED",
  "EXIT_INTENT_DETECTED",
]);
const DECISION_DEBOUNCE_MS = 3_100;
// A shopper who stops interacting stops emitting, so without a heartbeat a
// session that goes quiet mid-deliberation is never reconsidered. The backend
// gate still applies; most of these are answered with `debounce_active`.
const PERIODIC_DECISION_MS = 45_000;

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
  // The "started" flag is only persisted once delivery is confirmed (see markStarted
  // in SessionProvider below). If we set it optimistically here and the first
  // network attempt silently fails, this tab's session would never be retried and
  // every subsequent event would be rejected by the backend forever.
  const alreadyQueued = eventClient.pendingEvents().some((event) => (
    event.session_id === identity.sessionId && event.event_type === "SESSION_STARTED"
  ));
  if (!safeGet(startedKey) && !alreadyQueued) {
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
  const [latestDecision, setLatestDecision] = useState<DecisionResponse | null>(null);
  const creationRequest = useRef<Promise<unknown> | null>(null);
  const decisionTimer = useRef<number | null>(null);
  const pendingTrigger = useRef<EventType | null>(null);

  const requestDecision = useCallback(async (
    trigger: EventType | "PERIODIC",
    force = false,
  ): Promise<DecisionResponse | null> => {
    try {
      const response = await apiPost<DecisionResponse>(
        `/api/v1/sessions/${identity.sessionId}/decisions`,
        { trigger, force },
      );
      if (!response.suppressed && response.decision_id) setLatestDecision(response);
      return response;
    } catch {
      // Decision support is fail-open: commerce remains fully usable.
      return null;
    }
  }, [identity.sessionId]);

  useEffect(() => {
    const startedKey = `${SESSION_STARTED_PREFIX}${identity.sessionId}`;
    const markStarted = () => safeSet(startedKey, "1");

    if (creationRequest.current === null) {
      creationRequest.current = apiPost<{ session_id: string }>("/api/v1/sessions", {
        session_id: identity.sessionId,
        device_type: window.innerWidth < 768 ? "MOBILE" : "DESKTOP",
        referral_source: document.referrer ? "REFERRAL" : "DIRECT",
      }).then(() => markStarted())
        .catch((error: unknown) => {
          // The row already exists either way; only a genuine delivery failure
          // (network/5xx) should fall through to the queued SESSION_STARTED event,
          // which confirms via the subscribe callback below once it lands.
          if (error instanceof ApiError && error.status === 409) markStarted();
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
    // Exit intent, emitted at most once per session: the cursor leaving through
    // the top of the viewport (heading for the tab bar or address bar), or the
    // tab being backgrounded. Both are the last moment help can still land.
    let exitSignalled = false;
    const signalExit = (signal: "POINTER_EXIT" | "TAB_HIDDEN") => {
      if (exitSignalled) return;
      exitSignalled = true;
      eventClient.emit("EXIT_INTENT_DETECTED", { metadata: { signal } });
    };
    const onPointerOut = (event: MouseEvent) => {
      if (event.relatedTarget === null && event.clientY <= 0) signalExit("POINTER_EXIT");
    };
    const onVisibility = () => {
      if (document.visibilityState === "hidden") signalExit("TAB_HIDDEN");
    };
    document.addEventListener("mouseout", onPointerOut);
    document.addEventListener("visibilitychange", onVisibility);

    window.addEventListener("pagehide", endSession);
    const heartbeat = window.setInterval(() => {
      if (document.visibilityState === "visible") void requestDecision("PERIODIC");
    }, PERIODIC_DECISION_MS);
    const unsubscribe = eventClient.subscribe((events) => {
      if (events.some((event) => (
        event.session_id === identity.sessionId && event.event_type === "SESSION_STARTED"
      ))) {
        markStarted();
      }
      const trigger = [...events].reverse().find((event) => (
        DECISION_TRIGGER_TYPES.has(event.event_type)
      ));
      if (!trigger) return;
      pendingTrigger.current = trigger.event_type;
      if (decisionTimer.current !== null) window.clearTimeout(decisionTimer.current);
      decisionTimer.current = window.setTimeout(() => {
        const nextTrigger = pendingTrigger.current;
        pendingTrigger.current = null;
        decisionTimer.current = null;
        if (nextTrigger) void requestDecision(nextTrigger);
      }, DECISION_DEBOUNCE_MS);
    });
    return () => {
      window.removeEventListener("pagehide", endSession);
      document.removeEventListener("mouseout", onPointerOut);
      document.removeEventListener("visibilitychange", onVisibility);
      window.clearInterval(heartbeat);
      unsubscribe();
      if (decisionTimer.current !== null) window.clearTimeout(decisionTimer.current);
    };
  }, [identity, requestDecision]);

  // Stable across renders. Effects that emit on mount list `emit` as a
  // dependency, so an identity that changed whenever a decision arrived would
  // re-run them — re-emitting REVIEW_OPENED, which requests another decision,
  // which changes the identity again. That loop floods the event buffer.
  const emit = useCallback<SessionContextValue["emit"]>(
    (eventType, input) => eventClient.emit(eventType, input),
    [],
  );

  const value = useMemo<SessionContextValue>(() => ({
    sessionId: identity.sessionId,
    emit,
    latestDecision,
    requestDecision,
    clearDecision: (decisionId) => setLatestDecision((current) => (
      !decisionId || current?.decision_id === decisionId ? null : current
    )),
  }), [emit, identity.sessionId, latestDecision, requestDecision]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used within SessionProvider");
  return context;
}
