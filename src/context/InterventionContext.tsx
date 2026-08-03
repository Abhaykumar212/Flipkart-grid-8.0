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
import { useLocation } from "react-router-dom";
import { apiGet, apiPost } from "../lib/api";
import {
  useSession,
  type DecisionResponse,
  type RecommendedIntervention,
} from "./SessionContext";

const DISMISSED_KEY = "fk-dismissed-decisions-v1";

export interface AuthorizedIntervention extends RecommendedIntervention {
  decision_id: string;
}
interface LatestInterventionResponse {
  decision_id: string;
  recommended_intervention: RecommendedIntervention;
  explanation?: Record<string, unknown>;
}

interface InterventionContextValue {
  intervention: AuthorizedIntervention | null;
  explanation: Record<string, unknown> | null;
  shown: (surface: string) => void;
  click: () => void;
  dismiss: () => void;
}

const InterventionContext = createContext<InterventionContextValue | null>(null);

function dismissedIds(): Set<string> {
  try {
    const parsed: unknown = JSON.parse(window.sessionStorage.getItem(DISMISSED_KEY) ?? "[]");
    return new Set(Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === "string") : []);
  } catch {
    return new Set();
  }
}

function authorized(decision: DecisionResponse | null): AuthorizedIntervention | null {
  const recommended = decision?.recommended_intervention;
  if (
    decision?.decision !== "INTERVENE"
    || !decision.decision_id
    || !recommended
    || recommended.type === "NO_ACTION"
    || recommended.decision_id !== decision.decision_id
    || dismissedIds().has(decision.decision_id)
  ) return null;
  return { ...recommended, decision_id: decision.decision_id };
}

export function InterventionProvider({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const { sessionId, latestDecision, clearDecision, emit } = useSession();
  const [fallback, setFallback] = useState<DecisionResponse | null>(null);
  const shownIds = useRef(new Set<string>());
  const currentDecision = latestDecision ?? fallback;
  const intervention = authorized(currentDecision);

  useEffect(() => {
    let current = true;
    void apiGet<LatestInterventionResponse | undefined>(
      `/api/v1/sessions/${sessionId}/interventions/latest`,
    ).then((response) => {
      if (!current || !response?.decision_id) return;
      setFallback({
        decision_id: response.decision_id,
        session_id: sessionId,
        decision: "INTERVENE",
        recommended_intervention: response.recommended_intervention,
        explanation: response.explanation,
        suppressed: false,
      });
    }).catch(() => undefined);
    return () => { current = false; };
  }, [pathname, sessionId]);

  const shown = useCallback((surface: string) => {
    if (!intervention || shownIds.current.has(intervention.decision_id)) return;
    shownIds.current.add(intervention.decision_id);
    void apiPost(`/api/v1/decisions/${intervention.decision_id}/impression`, { surface })
      .catch(() => undefined);
    emit("INTERVENTION_SHOWN", {
      metadata: {
        decision_id: intervention.decision_id,
        intervention_id: intervention.type,
        surface,
      },
    });
  }, [emit, intervention]);

  const click = useCallback(() => {
    if (!intervention) return;
    void apiPost(`/api/v1/decisions/${intervention.decision_id}/outcome`, { clicked: true })
      .catch(() => undefined);
    emit("INTERVENTION_CLICKED", {
      metadata: {
        decision_id: intervention.decision_id,
        intervention_id: intervention.type,
      },
    });
  }, [emit, intervention]);

  const dismiss = useCallback(() => {
    if (!intervention) return;
    void apiPost(`/api/v1/decisions/${intervention.decision_id}/outcome`, { dismissed: true })
      .catch(() => undefined);
    const ids = dismissedIds();
    ids.add(intervention.decision_id);
    try {
      window.sessionStorage.setItem(DISMISSED_KEY, JSON.stringify([...ids]));
    } catch {
      // Local hiding still succeeds when storage is unavailable.
    }
    emit("INTERVENTION_DISMISSED", {
      metadata: {
        decision_id: intervention.decision_id,
        intervention_id: intervention.type,
      },
    });
    setFallback(null);
    clearDecision(intervention.decision_id);
  }, [clearDecision, emit, intervention]);

  const value = useMemo<InterventionContextValue>(() => ({
    intervention,
    explanation: currentDecision?.explanation ?? null,
    shown,
    click,
    dismiss,
  }), [click, currentDecision?.explanation, dismiss, intervention, shown]);

  return <InterventionContext.Provider value={value}>{children}</InterventionContext.Provider>;
}

export function useIntervention(): InterventionContextValue {
  const context = useContext(InterventionContext);
  if (!context) throw new Error("useIntervention must be used within InterventionProvider");
  return context;
}
