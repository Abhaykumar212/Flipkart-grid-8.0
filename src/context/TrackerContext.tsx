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
import { apiGet } from "../lib/api";
import { eventClient } from "../lib/events";
import { useSession } from "./SessionContext";

export interface SessionSnapshot {
  session: {
    session_id: string;
    user_id: string | null;
    started_at: string;
    last_event_at: string | null;
    device_type: string | null;
    referral_source: string | null;
    current_product_id: string | null;
    current_route: string | null;
    ended: boolean;
    order_completed: boolean;
  };
  cart: {
    value: number;
    mrp_total: number;
    item_count: number;
    delivery_fee: number;
    promo_code: string | null;
    items: Array<{
      product_id: string;
      quantity: number;
      unit_price: number;
      variant?: string | null;
      added_at: string;
    }>;
    first_add_at: string | null;
  };
  counters: Record<string, number>;
  current_features: Record<string, number> | null;
  feature_schema_version: string | null;
  latest_decision: Record<string, unknown> | null;
  interventions: {
    shown: Array<Record<string, unknown>>;
    dismissal_count: number;
    click_count: number;
    last_shown_at: string | null;
  };
}

interface TrackerContextValue {
  snapshot: SessionSnapshot | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

const TrackerContext = createContext<TrackerContextValue | null>(null);
const REFRESH_INTERVAL_MS = 5_000;

export function TrackerProvider({ children }: { children: ReactNode }) {
  const { sessionId } = useSession();
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestNumber = useRef(0);

  const load = useCallback(async () => {
    const currentRequest = ++requestNumber.current;
    setLoading(true);
    try {
      const state = await apiGet<SessionSnapshot>(`/api/v1/sessions/${sessionId}`);
      if (currentRequest !== requestNumber.current) return;
      setSnapshot(state);
      setError(null);
    } catch (requestError) {
      if (currentRequest !== requestNumber.current) return;
      setError(requestError instanceof Error ? requestError.message : "Session API unavailable");
    } finally {
      if (currentRequest === requestNumber.current) setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void load();
    const interval = window.setInterval(() => void load(), REFRESH_INTERVAL_MS);
    const unsubscribe = eventClient.subscribe(() => void load());
    return () => {
      window.clearInterval(interval);
      unsubscribe();
      requestNumber.current += 1;
    };
  }, [load]);

  const value = useMemo<TrackerContextValue>(() => ({
    snapshot,
    loading,
    error,
    refresh: () => void load(),
  }), [error, load, loading, snapshot]);

  return <TrackerContext.Provider value={value}>{children}</TrackerContext.Provider>;
}

export function useTracker(): TrackerContextValue {
  const context = useContext(TrackerContext);
  if (!context) throw new Error("useTracker must be used within TrackerProvider");
  return context;
}
