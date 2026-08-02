import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet, apiUrl } from "../lib/api";
import type {
  DashboardEvent,
  DashboardStreamStatus,
} from "../types/dashboard";

type EventHandler = (event: DashboardEvent) => void;

export function useDashboardStream(
  onEvent?: EventHandler,
  onOpen?: () => void,
) {
  const eventHandler = useRef(onEvent);
  const openHandler = useRef(onOpen);
  const [status, setStatus] = useState<DashboardStreamStatus>("connecting");
  const [lastEvent, setLastEvent] = useState<DashboardEvent | null>(null);
  const [eventCount, setEventCount] = useState(0);
  eventHandler.current = onEvent;
  openHandler.current = onOpen;

  useEffect(() => {
    const source = new EventSource(apiUrl("/api/v1/dashboard/stream"));
    const receive = (type: DashboardEvent["type"]) => (message: Event) => {
      const raw = message as MessageEvent<string>;
      const dashboardEvent: DashboardEvent = {
        id: raw.lastEventId,
        type,
        data: JSON.parse(raw.data) as Record<string, unknown>,
      };
      setLastEvent(dashboardEvent);
      setEventCount((value) => value + 1);
      eventHandler.current?.(dashboardEvent);
    };
    const onIngested = receive("event_ingested");
    const onDecision = receive("decision_made");
    source.addEventListener("event_ingested", onIngested);
    source.addEventListener("decision_made", onDecision);
    source.onopen = () => {
      setStatus("connected");
      openHandler.current?.();
    };
    source.onerror = () => setStatus("reconnecting");
    return () => {
      source.removeEventListener("event_ingested", onIngested);
      source.removeEventListener("decision_made", onDecision);
      source.close();
    };
  }, []);

  return { status, lastEvent, eventCount };
}

export function useDashboardResource<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activeRequest = useRef(0);

  const refresh = useCallback(async () => {
    const requestId = ++activeRequest.current;
    try {
      const response = await apiGet<T>(path);
      if (requestId !== activeRequest.current) return;
      setData(response);
      setError(null);
    } catch (reason) {
      if (requestId !== activeRequest.current) return;
      setError(reason instanceof Error ? reason.message : "Dashboard request failed");
    } finally {
      if (requestId === activeRequest.current) setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    setLoading(true);
    void refresh();
    return () => {
      activeRequest.current += 1;
    };
  }, [refresh]);

  const stream = useDashboardStream(() => void refresh(), () => void refresh());
  return { data, loading, error, refresh, stream };
}
