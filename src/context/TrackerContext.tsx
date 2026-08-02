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
import { useWishlist } from "./WishlistContext";
import { productById } from "../data/products";
import { computeCartTotals } from "../lib/cartTotals";
import { userHistory } from "../lib/userHistory";
import {
  materialSignature,
  sessionTracker,
  type CartContextPayload,
  type PredictionResponse,
  type ShopperProfilePayload,
  type TrackerSnapshot,
} from "../lib/tracker";
import { pipelineTrace, type RootCauseResponse } from "../lib/pipelineTrace";

const EVIDENCE_WARMUP_MS = 10_000;
const PREDICTION_DEBOUNCE_MS = 700;
const LIVE_REFRESH_MS = 5_000;

/**
 * Client-side guard so we don't POST to the RCA endpoint on every 5s poll.
 * The backend gate is authoritative (it also dedupes and budgets), but there is
 * no point paying a round trip when the local probability is clearly below it.
 */
const RCA_TRIGGER_PROBABILITY = 0.8;

interface TrackerContextValue {
  snapshot: TrackerSnapshot;
  prediction: PredictionResponse | null;
  loading: boolean;
  error: string | null;
  warmupRemainingSeconds: number;
  /** Most recent completed root-cause analysis, if any. */
  rootCause: RootCauseResponse | null;
  rootCauseLoading: boolean;
  recordProductVisit: (productId: string) => void;
  recordReviewVisibility: () => void;
  recordSearch: (query: string) => void;
  recordPincodeCheck: (pincode: string) => void;
  requestPrediction: () => void;
  /** Manual "Re-run analysis" — bypasses dedup/cooldown server-side. */
  runRootCauseAnalysis: (options?: { force?: boolean; scenarioLabel?: string }) => Promise<void>;
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
  const { productIds: wishlistProductIds } = useWishlist();
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
  const [rootCause, setRootCause] = useState<RootCauseResponse | null>(null);
  const [rootCauseLoading, setRootCauseLoading] = useState(false);
  const rcaController = useRef<AbortController | null>(null);
  const lastAnalysedSignature = useRef<string | null>(null);

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

  const snapshot = useMemo(() => sessionTracker.getSnapshot(now), [revision, now]);
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

  // Callers such as the scenario loader mutate the cart and then invoke the
  // analysis a moment later. Reading `items`/`totals` from a captured closure
  // would hand the agent the *previous* cart (cart_age_seconds: 0, no lines),
  // so the live values are mirrored into refs and read at call time.
  const itemsRef = useRef(items);
  const totalsRef = useRef(totals);
  const routeRef = useRef(location.pathname);
  const wishlistRef = useRef(wishlistProductIds);
  itemsRef.current = items;
  totalsRef.current = totals;
  routeRef.current = location.pathname;
  wishlistRef.current = wishlistProductIds;

  /** Real (if lightweight) shopper history — wishlist, views, past purchases. */
  const buildShopperProfile = useCallback((): ShopperProfilePayload => {
    const history = userHistory.getSnapshot();
    return {
      wishlist_product_ids: wishlistRef.current,
      recent_view_product_ids: history.recentViewProductIds,
      past_purchase_product_ids: history.pastPurchaseProductIds,
    };
  }, []);

  /** Snapshot the cart in the shape the agent needs to be concrete about it. */
  const buildCartContext = useCallback((): CartContextPayload => {
    const items = itemsRef.current;
    const totals = totalsRef.current;
    const startedAtMs = cartStartedAt(items);
    return {
      lines: items.flatMap((item) => {
        const product = productById.get(item.productId);
        if (!product) return [];
        const history = product.signals?.priceHistory ?? [];
        const previous = history.at(-2)?.price;
        const latest = history.at(-1)?.price;
        return [{
          product_id: product.id,
          title: product.title,
          brand: product.brand,
          category: product.category,
          quantity: item.quantity,
          selling_price: product.price.sellingPrice,
          mrp: product.price.mrp,
          discount_percent: product.price.mrp > 0
            ? Math.round(((product.price.mrp - product.price.sellingPrice) / product.price.mrp) * 100)
            : 0,
          estimated_delivery_days: product.delivery.estimatedDays,
          in_stock: product.stock.inStock,
          price_dropped_recently:
            previous !== undefined && latest !== undefined && latest < previous,
        }];
      }),
      cart_total: totals.totalSellingPrice,
      mrp_total: totals.totalMrp,
      delivery_fee: totals.deliveryCharge,
      currency: "INR",
      cart_age_seconds: startedAtMs === null ? 0 : Math.max(0, (Date.now() - startedAtMs) / 1000),
      current_route: routeRef.current,
    };
    // Reads only refs, so the identity is stable and never serves stale data.
  }, []);

  const runRootCauseAnalysis = useCallback(
    async (options: { force?: boolean; scenarioLabel?: string } = {}) => {
      const telemetryStart = performance.now();
      // Claim the signature immediately, not on success. Otherwise the
      // auto-trigger effect fires again on the same render and we pay for two
      // identical analyses per scenario load.
      lastAnalysedSignature.current = materialSignature(sessionTracker.getSnapshot().features);

      const runId = pipelineTrace.startRun(options.force ? "manual" : "auto", options.scenarioLabel);
      rcaController.current?.abort();
      const controller = new AbortController();
      rcaController.current = controller;
      setRootCauseLoading(true);

      try {
        const cartContext = buildCartContext();
        pipelineTrace.attachTelemetry(
          runId,
          {
            features: sessionTracker.getSnapshot().features,
            cart_lines: cartContext.lines.length,
            cart_total: cartContext.cart_total,
            route: cartContext.current_route,
          },
          performance.now() - telemetryStart,
        );

        const result = (await sessionTracker.requestRootCause(cartContext, buildShopperProfile(), {
          force: options.force,
          signal: controller.signal,
        })) as RootCauseResponse;

        pipelineTrace.completeRun(runId, result);
        // Rewritten to the frontend-local run id: the backend's own uuid is
        // only ever used for this dedup key (never sent back to the server),
        // and InterventionContext needs it to attach a delivery decision to
        // the matching entry in pipelineTrace, which is keyed by the local id.
        setRootCause({ ...result, pipeline_run_id: runId });
      } catch (requestError) {
        if (controller.signal.aborted) {
          // Superseded by a newer request — close the run out instead of
          // leaving it spinning in the history forever.
          pipelineTrace.abortRun(runId);
          return;
        }
        pipelineTrace.failRun(
          runId,
          requestError instanceof Error ? requestError.message : "Root cause request failed",
        );
      } finally {
        if (!controller.signal.aborted) setRootCauseLoading(false);
      }
    },
    [buildCartContext, buildShopperProfile],
  );

  // Auto-trigger: fire once when the session first crosses the high-risk
  // threshold, and again only if the feature vector materially changes.
  useEffect(() => {
    const probability = prediction?.abandonment_probability ?? 0;
    if (probability < RCA_TRIGGER_PROBABILITY) return;
    if (warmupRemainingMs > 0) return;
    if (rootCauseLoading) return;

    // Key on material features only. Dwell-time features tick every second, so
    // hashing the whole vector would re-fire the agent on every render.
    const signature = materialSignature(snapshot.features);
    if (signature === lastAnalysedSignature.current) return;

    // Claim the signature before the request so concurrent renders don't
    // double-fire while the first call is still in flight.
    lastAnalysedSignature.current = signature;
    void runRootCauseAnalysis();
  }, [
    prediction?.abandonment_probability,
    warmupRemainingMs,
    rootCauseLoading,
    snapshot.features,
    runRootCauseAnalysis,
  ]);

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

  const value = useMemo<TrackerContextValue>(() => ({
    snapshot,
    prediction,
    loading,
    error,
    warmupRemainingSeconds: Math.ceil(warmupRemainingMs / 1_000),
    rootCause,
    rootCauseLoading,
    recordProductVisit: (productId) => sessionTracker.recordProductVisit(productId),
    recordReviewVisibility: () => sessionTracker.recordReviewVisibility(),
    recordSearch: (query) => sessionTracker.recordSearch(query),
    recordPincodeCheck: (pincode) => sessionTracker.recordPincodeCheck(pincode),
    requestPrediction,
    runRootCauseAnalysis,
  }), [
    snapshot,
    prediction,
    loading,
    error,
    warmupRemainingMs,
    rootCause,
    rootCauseLoading,
    requestPrediction,
    runRootCauseAnalysis,
  ]);

  return <TrackerContext.Provider value={value}>{children}</TrackerContext.Provider>;
}

export function useTracker(): TrackerContextValue {
  const context = useContext(TrackerContext);
  if (!context) throw new Error("useTracker must be used within TrackerProvider");
  return context;
}
