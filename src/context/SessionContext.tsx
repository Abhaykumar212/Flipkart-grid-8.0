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
]);
const DECISION_DEBOUNCE_MS = 3_100;

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
    const unsubscribe = eventClient.subscribe((events) => {
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
      unsubscribe();
      if (decisionTimer.current !== null) window.clearTimeout(decisionTimer.current);
    };
  }, [identity, requestDecision]);

  const value = useMemo<SessionContextValue>(() => ({
    sessionId: identity.sessionId,
    emit: (eventType, input) => eventClient.emit(eventType, input),
    latestDecision,
    requestDecision,
    clearDecision: (decisionId) => setLatestDecision((current) => (
      !decisionId || current?.decision_id === decisionId ? null : current
    )),
  }), [identity.sessionId, latestDecision, requestDecision]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used within SessionProvider");
  return context;
}
