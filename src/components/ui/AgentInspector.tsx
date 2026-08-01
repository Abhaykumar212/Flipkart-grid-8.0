import { useState } from "react";
import {
  Activity,
  BarChart3,
  BrainCircuit,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  X,
} from "lucide-react";
import { useTracker } from "../../context/TrackerContext";
import {
  ABANDONMENT_FEATURE_NAMES,
  type AbandonmentFeatureName,
} from "../../lib/tracker";

const FEATURE_LABELS: Record<AbandonmentFeatureName, string> = {
  // A. Cart engagement
  seconds_spent_in_cart: "Time in cart",
  times_returned_to_product_page: "Returns to product",
  product_reviews_read: "Reviews read",
  seconds_idle_before_checkout: "Idle before checkout",
  delivery_pincode_checks: "Pincode checks",
  saved_items_in_wishlist: "Wishlist items",
  // B. Cost friction
  cart_value_vs_typical_order: "Cart vs usual order",
  delivery_fee_percent_of_cart: "Delivery fee share",
  price_dropped_since_first_view: "Price dropped",
  discount_seeking_tendency: "Discount seeking",
  failed_coupon_attempts: "Failed coupons",
  // C. Delivery friction
  estimated_delivery_days: "Est. delivery",
  // D. Checkout & trust friction
  payment_method_on_file: "Card on file",
  checkout_steps_completed: "Checkout progress",
  payment_attempts_failed: "Failed payments",
  is_guest_checkout: "Guest checkout",
  // E. Customer history
  past_abandonment_rate: "Past abandonment",
  past_order_return_rate: "Past returns",
  lifetime_orders_placed: "Lifetime orders",
  days_since_last_purchase: "Days since order",
  // F. Session context
  is_mobile_session: "Mobile session",
  is_late_night_session: "Late-night session",
};

const BOOLEAN_FEATURES = new Set<AbandonmentFeatureName>([
  "price_dropped_since_first_view",
  "payment_method_on_file",
  "is_guest_checkout",
  "is_mobile_session",
  "is_late_night_session",
]);

const RATE_FEATURES = new Set<AbandonmentFeatureName>([
  "past_abandonment_rate",
  "discount_seeking_tendency",
  "past_order_return_rate",
]);

function percentage(value: number): string {
  return `${(Math.max(0, Math.min(1, value)) * 100).toFixed(1)}%`;
}

function featureValue(name: AbandonmentFeatureName, value: number): string {
  if (BOOLEAN_FEATURES.has(name)) return value ? "Yes" : "No";
  if (RATE_FEATURES.has(name)) return percentage(value);
  if (name === "seconds_spent_in_cart" || name === "seconds_idle_before_checkout") {
    return `${value}s`;
  }
  if (name === "delivery_fee_percent_of_cart") return `${value.toFixed(2)}%`;
  if (name === "estimated_delivery_days") return `${value} days`;
  if (name === "days_since_last_purchase") return `${value}d`;
  if (name === "checkout_steps_completed") return `${value} / 3`;
  if (name === "cart_value_vs_typical_order") return `${value.toFixed(2)}x`;
  return Number.isInteger(value) ? String(value) : value.toFixed(3);
}

/**
 * Tier comes from the API, not recomputed here — the backend owns the
 * thresholds that Phase 2 will fire on, so there is exactly one source of truth.
 */
const RISK_STYLES = {
  high: { label: "High", text: "text-red-600", bar: "bg-red-500", bg: "bg-red-50" },
  medium: { label: "Medium", text: "text-amber-600", bar: "bg-amber-500", bg: "bg-amber-50" },
  low: { label: "Low", text: "text-emerald-600", bar: "bg-emerald-500", bg: "bg-emerald-50" },
} as const;

export function AgentInspector() {
  const [isOpen, setIsOpen] = useState(false);
  const {
    snapshot,
    prediction,
    loading,
    error,
    warmupRemainingSeconds,
    requestPrediction,
  } = useTracker();

  if (!snapshot.signals.cartActive) return null;

  const probability = prediction?.abandonment_probability ?? 0;
  const risk = RISK_STYLES[prediction?.risk_tier ?? "low"];
  const topFeatures = prediction?.top_contributing_features.slice(0, 3) ?? [];
  const impacts = Object.entries(prediction?.feature_impacts ?? {}).sort(
    ([, left], [, right]) => Math.abs(right) - Math.abs(left),
  );
  const status = loading
    ? "Scoring"
    : warmupRemainingSeconds > 0
      ? `Warmup ${warmupRemainingSeconds}s`
      : prediction
        ? percentage(probability)
        : "Awaiting model";

  return (
    <div className="fixed bottom-5 right-5 z-[9999]">
      {isOpen && (
        <section className="absolute bottom-16 right-0 flex max-h-[84vh] w-[min(500px,calc(100vw-24px))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_24px_70px_rgba(15,23,42,0.28)]">
          <header className="bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950 px-5 py-4 text-white">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/20 text-blue-300">
                  <BrainCircuit className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-base font-bold">Phase 1 Risk Inspector</h2>
                  <p className="text-[11px] text-slate-400">Live features · XGBoost · SHAP</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={requestPrediction}
                  disabled={loading || warmupRemainingSeconds > 0}
                  className="rounded-lg p-2 text-slate-400 transition hover:bg-white/10 hover:text-white disabled:opacity-40"
                  aria-label="Refresh prediction"
                >
                  <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                </button>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="rounded-lg p-2 text-slate-400 transition hover:bg-white/10 hover:text-white"
                  aria-label="Close risk inspector"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div className="mt-4 flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px]">
              <span className="flex items-center gap-2 text-slate-300">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Active cart telemetry
              </span>
              <span className="font-medium text-blue-300">
                {ABANDONMENT_FEATURE_NAMES.length} live session features
              </span>
            </div>
          </header>

          <div className="overflow-y-auto p-5">
            {error && (
              <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                Model unavailable: {error}
              </div>
            )}

            <div className="grid grid-cols-[1.35fr_1fr] gap-3">
              <div className={`rounded-xl border border-slate-200 p-4 ${risk.bg}`}>
                <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  <span>Abandonment probability</span>
                  {prediction && <span className={risk.text}>{risk.label}</span>}
                </div>
                <div className={`mt-1 text-3xl font-black ${prediction ? risk.text : "text-slate-400"}`}>
                  {prediction ? percentage(probability) : "—"}
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-white">
                  <div
                    className={`h-full rounded-full transition-all ${risk.bar}`}
                    style={{ width: prediction ? percentage(probability) : "0%" }}
                  />
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Confidence</div>
                <div className="mt-1 text-2xl font-black text-blue-600">
                  {prediction ? percentage(prediction.confidence_score) : "—"}
                </div>
                <p className="mt-2 text-[10px] text-slate-500">XGBoost model response</p>
              </div>
            </div>

            <h3 className="mb-2 mt-5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Live feature vector
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {ABANDONMENT_FEATURE_NAMES.map((name) => (
                <div key={name} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
                  <div className="truncate text-[10px] text-slate-500" title={name}>{FEATURE_LABELS[name]}</div>
                  <div className="mt-0.5 text-sm font-bold text-slate-900">
                    {featureValue(name, snapshot.features[name])}
                  </div>
                </div>
              ))}
            </div>

            <h3 className="mb-2 mt-5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Top 3 SHAP attributions
            </h3>
            {topFeatures.length > 0 ? (
              <div className="space-y-2">
                {topFeatures.map(({ feature, shap_value }, index) => (
                  <div key={`${feature}-${index}`} className="flex items-center gap-3 rounded-xl border border-slate-200 p-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-xs font-black text-blue-700">
                      {index + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-xs font-semibold text-slate-800">{feature}</div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className={`h-full rounded-full ${shap_value >= 0 ? "bg-red-500" : "bg-emerald-500"}`}
                          style={{ width: `${Math.min(100, Math.abs(shap_value) * 100)}%` }}
                        />
                      </div>
                    </div>
                    <span className={`text-xs font-bold ${shap_value >= 0 ? "text-red-600" : "text-emerald-600"}`}>
                      {shap_value >= 0 ? "+" : ""}{shap_value.toFixed(4)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 p-4 text-center text-xs text-slate-500">
                {warmupRemainingSeconds > 0
                  ? `Collecting evidence for ${warmupRemainingSeconds}s before the first prediction.`
                  : "SHAP values will appear after a successful prediction."}
              </div>
            )}

            <h3 className="mb-2 mt-5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              All feature impacts
            </h3>
            {impacts.length > 0 ? (
              <div className="overflow-hidden rounded-xl border border-slate-200">
                {impacts.map(([feature, impact]) => (
                  <div key={feature} className="flex items-center gap-3 border-b border-slate-100 px-3 py-2.5 last:border-0">
                    {impact >= 0
                      ? <ChevronUp className="h-4 w-4 shrink-0 text-red-500" />
                      : <ChevronDown className="h-4 w-4 shrink-0 text-emerald-500" />}
                    <span className="min-w-0 flex-1 truncate text-[11px] font-medium text-slate-700" title={feature}>{feature}</span>
                    <span className={`text-xs font-bold ${impact >= 0 ? "text-red-600" : "text-emerald-600"}`}>
                      {impact >= 0 ? "+" : ""}{impact.toFixed(4)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-xl bg-slate-50 p-3 text-center text-xs text-slate-500">No model impacts yet.</div>
            )}
          </div>
        </section>
      )}

      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="flex items-center gap-3 rounded-full border border-white/20 bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-white shadow-[0_10px_30px_rgba(37,99,235,0.35)] transition hover:-translate-y-0.5"
      >
        <span className="relative flex h-8 w-8 items-center justify-center rounded-full bg-white/15">
          {prediction ? <BarChart3 className="h-5 w-5" /> : <Activity className="h-5 w-5" />}
          <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-blue-600 bg-emerald-400" />
        </span>
        <span className="text-left">
          <span className="block text-xs font-bold leading-4">Phase 1 Risk</span>
          <span className="block text-[10px] text-blue-100">XGBoost + SHAP</span>
        </span>
        <span className="ml-1 rounded-full bg-white/15 px-2.5 py-1 text-[10px] font-bold text-white">{status}</span>
      </button>
    </div>
  );
}
