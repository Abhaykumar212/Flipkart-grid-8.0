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
import { useCart } from "./CartContext";
import { productById } from "../data/products";
import { computeCartTotals } from "../lib/cartTotals";
import {
  sessionTracker,
  type PredictionResponse,
  type TrackerSnapshot,
} from "../lib/tracker";

const EVIDENCE_WARMUP_MS = 10_000;
const PREDICTION_DEBOUNCE_MS = 700;
const LIVE_REFRESH_MS = 5_000;

interface TrackerContextValue {
  snapshot: TrackerSnapshot;
  prediction: PredictionResponse | null;
  loading: boolean;
  error: string | null;
  warmupRemainingSeconds: number;
  recordProductVisit: (productId: string) => void;
  recordReviewVisibility: () => void;
  recordSearch: (query: string) => void;
  recordPincodeCheck: (pincode: string) => void;
  requestPrediction: () => void;
}

const TrackerContext = createContext<TrackerContextValue | null>(null);

function cartStartedAt(items: ReturnType<typeof useCart>["items"]): number | null {
  const timestamps = items
    .map((item) => Date.parse(item.addedAt))
    .filter(Number.isFinite);
  return timestamps.length > 0 ? Math.min(...timestamps) : null;
}

export function TrackerProvider({ children }: { children: ReactNode }) {
  const { items } = useCart();
  const location = useLocation();
  const totals = computeCartTotals(items);
  const [revision, setRevision] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestSequence = useRef(0);
  const requestController = useRef<AbortController | null>(null);
  const debounceTimer = useRef<number | null>(null);

  useEffect(() => sessionTracker.subscribe(() => setRevision((value) => value + 1)), []);

  useEffect(() => {
    sessionTracker.recordRoute(location.pathname);
  }, [location.pathname]);

  useEffect(() => {
    const products = items.flatMap((item) => {
      const product = productById.get(item.productId);
      if (!product) return [];
      const history = product.signals?.priceHistory ?? [];
      const previousPrice = history.at(-2)?.price;
      const latestPrice = history.at(-1)?.price;

      return [{
        id: product.id,
        quantity: item.quantity,
        sellingPrice: product.price.sellingPrice,
        mrp: product.price.mrp,
        deliveryFee: 0,
        estimatedDeliveryDays: product.delivery.estimatedDays,
        priceDroppedRecently:
          previousPrice !== undefined && latestPrice !== undefined && latestPrice < previousPrice,
        addedAt: item.addedAt,
      }];
    });

    sessionTracker.recordCart({
      products,
      itemCount: totals.itemCount,
      cartValue: totals.totalSellingPrice,
      deliveryFee: totals.deliveryCharge,
    });
  }, [items, totals.itemCount, totals.totalSellingPrice, totals.deliveryCharge]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let lastRecordedAt = 0;
    const recordActivity = () => {
      const timestamp = Date.now();
      if (timestamp - lastRecordedAt < 1_000) return;
      lastRecordedAt = timestamp;
      sessionTracker.recordActivity(timestamp);
    };
    window.addEventListener("pointerdown", recordActivity, { passive: true });
    window.addEventListener("keydown", recordActivity);
    return () => {
      window.removeEventListener("pointerdown", recordActivity);
      window.removeEventListener("keydown", recordActivity);
    };
  }, []);

  const snapshot = useMemo(() => {
    void revision;
    return sessionTracker.getSnapshot(now);
  }, [revision, now]);
  const startedAt = cartStartedAt(items);
  const warmupRemainingMs = startedAt === null
    ? 0
    : Math.max(0, EVIDENCE_WARMUP_MS - (now - startedAt));

  const runPrediction = useCallback(async () => {
    const current = sessionTracker.getSnapshot();
    if (!current.signals.cartActive) {
      requestSequence.current += 1;
      requestController.current?.abort();
      setPrediction(null);
      setLoading(false);
      setError(null);
      return;
    }

    const currentStartedAt = cartStartedAt(items);
    if (currentStartedAt !== null && Date.now() - currentStartedAt < EVIDENCE_WARMUP_MS) return;

    const sequence = ++requestSequence.current;
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setLoading(true);
    setError(null);

    try {
      const result = await sessionTracker.predict(controller.signal);
      if (sequence !== requestSequence.current) return;
      setPrediction(result);
    } catch (requestError) {
      if (controller.signal.aborted || sequence !== requestSequence.current) return;
      setError(requestError instanceof Error ? requestError.message : "Prediction request failed");
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
    }
  }, [items]);

  const requestPrediction = useCallback(() => {
    if (debounceTimer.current !== null) window.clearTimeout(debounceTimer.current);
    debounceTimer.current = window.setTimeout(runPrediction, PREDICTION_DEBOUNCE_MS);
  }, [runPrediction]);

  useEffect(() => {
    if (!snapshot.signals.cartActive) {
      runPrediction();
      return;
    }

    requestPrediction();
    const refresh = window.setInterval(requestPrediction, LIVE_REFRESH_MS);
    return () => {
      window.clearInterval(refresh);
      if (debounceTimer.current !== null) window.clearTimeout(debounceTimer.current);
    };
  }, [revision, snapshot.signals.cartActive, requestPrediction, runPrediction]);

  useEffect(() => () => requestController.current?.abort(), []);

  const recordProductVisit = useCallback(
    (productId: string) => sessionTracker.recordProductVisit(productId),
    [],
  );
  const recordReviewVisibility = useCallback(
    () => sessionTracker.recordReviewVisibility(),
    [],
  );
  const recordSearch = useCallback((query: string) => sessionTracker.recordSearch(query), []);
  const recordPincodeCheck = useCallback(
    (pincode: string) => sessionTracker.recordPincodeCheck(pincode),
    [],
  );

  const value = useMemo<TrackerContextValue>(() => ({
    snapshot,
    prediction,
    loading,
    error,
    warmupRemainingSeconds: Math.ceil(warmupRemainingMs / 1_000),
    recordProductVisit,
    recordReviewVisibility,
    recordSearch,
    recordPincodeCheck,
    requestPrediction,
  }), [
    snapshot,
    prediction,
    loading,
    error,
    warmupRemainingMs,
    recordProductVisit,
    recordReviewVisibility,
    recordSearch,
    recordPincodeCheck,
    requestPrediction,
  ]);

  return <TrackerContext.Provider value={value}>{children}</TrackerContext.Provider>;
}

export function useTracker(): TrackerContextValue {
  const context = useContext(TrackerContext);
  if (!context) throw new Error("useTracker must be used within TrackerProvider");
  return context;
}
