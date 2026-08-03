import { useState } from "react";
import { Activity, ExternalLink, RefreshCw, ShieldCheck, Workflow, X } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useCart } from "../../context/CartContext";
import { useTracker } from "../../context/TrackerContext";
import { useSession } from "../../context/SessionContext";

const COUNTER_LABELS: Record<string, string> = {
  product_views: "Product views",
  distinct_products_viewed: "Distinct products",
  review_opens: "Review opens",
  review_dwell_ms: "Review dwell (ms)",
  similar_product_views: "Similar views",
  comparisons: "Comparisons",
  cart_views: "Cart views",
  cart_adds: "Cart adds",
  cart_removes: "Cart removes",
  searches: "Searches",
  price_sorts: "Price sorts",
  coupon_searches: "Coupon searches",
  delivery_checks: "Delivery checks",
  checkout_starts: "Checkout starts",
  checkout_max_step: "Checkout step",
  payment_failures: "Payment failures",
  payment_method_changes: "Payment changes",
};

interface ExplanationShape {
  observations?: Array<{ feature: string; value: number; statement: string }>;
  inference?: { root_cause?: string; probability?: number; statement?: string };
  action?: { statement?: string };
  rendered_text?: string;
}

function humanCause(cause: string): string {
  return cause
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b[a-z]/g, (character) => character.toUpperCase());
}

/**
 * The agent, made visible on the storefront itself.
 *
 * A reviewer browsing the shop should be able to see that something is
 * reasoning about them — the live risk, the diagnosis, and crucially the
 * decision to stay quiet, which is otherwise indistinguishable from a system
 * that simply is not running.
 */
export function AgentInspector() {
  const [isOpen, setIsOpen] = useState(false);
  const { pathname } = useLocation();
  const { count } = useCart();
  const { snapshot, loading, error, refresh } = useTracker();
  const { latestDecision } = useSession();

  if (count === 0 && (snapshot?.cart.item_count ?? 0) === 0) return null;

  const counters = Object.entries(snapshot?.counters ?? {})
    .filter(([name]) => name in COUNTER_LABELS && Number(snapshot?.counters?.[name]) > 0)
    .sort(([left], [right]) => left.localeCompare(right));

  const explanation = (latestDecision?.explanation ?? {}) as ExplanationShape;
  const probability = latestDecision?.abandonment_probability ?? null;
  const band = latestDecision?.risk_level ?? null;
  const decision = latestDecision?.decision;
  const intervention = latestDecision?.recommended_intervention;
  const displayPct =
    probability === null ? null : Math.min(99, Math.max(1, Math.round(probability * 100)));

  const bandColor =
    band === "HIGH" ? "bg-red-500" : band === "MEDIUM" ? "bg-fk-orange" : "bg-fk-green";
  const bandText =
    band === "HIGH" ? "text-red-600" : band === "MEDIUM" ? "text-fk-orange" : "text-fk-green";

  // The cart and checkout pages carry a sticky action bar on mobile, so the
  // launcher has to sit clear of it.
  const clearsMobileCheckoutBar = pathname === "/cart" || pathname === "/checkout";

  return (
    <div
      className={`fixed right-3 z-[9999] lg:bottom-5 lg:right-5 ${
        clearsMobileCheckoutBar ? "bottom-[calc(5.25rem+env(safe-area-inset-bottom))]" : "bottom-3"
      }`}
    >
      {isOpen && (
        <section className="absolute bottom-16 right-0 flex max-h-[min(76vh,720px)] w-[min(430px,calc(100vw-24px))] flex-col overflow-hidden rounded-[2px] border border-fk-border bg-white shadow-[0_24px_70px_rgba(15,23,42,0.28)]">
          <header className="bg-fk-footer px-5 py-4 text-white">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-bold">Shopping assistant</h2>
                <p className="text-fk-xs text-slate-400">
                  Watching this session · deciding in real time
                </p>
              </div>
              <div className="flex items-center gap-1">
                <Link
                  to="/pipeline"
                  onClick={() => setIsOpen(false)}
                  className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"
                  aria-label="Open pipeline console"
                >
                  <Workflow className="h-4 w-4" />
                </Link>
                <button
                  type="button"
                  onClick={refresh}
                  className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"
                  aria-label="Refresh session"
                >
                  <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                </button>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"
                  aria-label="Close assistant inspector"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <p className="mt-3 truncate rounded-[2px] border border-white/10 bg-white/5 px-3 py-2 font-mono text-fk-xs text-blue-200">
              {snapshot?.session.session_id ?? "Waiting for the event API"}
            </p>
          </header>

          <div className="overflow-y-auto">
            {error && (
              <p className="m-4 rounded-[2px] border border-amber-200 bg-amber-50 p-3 text-fk-sm text-amber-800">
                Events remain buffered while the API is unavailable.
              </p>
            )}

            {/* What the risk model currently thinks. */}
            <div className="border-b border-fk-border px-5 py-4">
              <div className="flex items-end justify-between gap-3">
                <p className="text-fk-xs font-bold uppercase tracking-wider text-fk-muted">
                  Abandonment risk
                </p>
                {band && (
                  <span className={`text-fk-sm font-bold ${bandText}`}>{band}</span>
                )}
              </div>
              {displayPct === null ? (
                <p className="mt-2 text-fk-base text-fk-muted">
                  Gathering evidence — no decision requested yet.
                </p>
              ) : (
                <>
                  <p className="mt-1 text-2xl font-bold text-fk-ink">{displayPct}%</p>
                  <span className="mt-2 block h-2 w-full overflow-hidden rounded-full bg-fk-bg">
                    <span
                      className={`block h-full rounded-full ${bandColor}`}
                      style={{ width: `${displayPct}%` }}
                    />
                  </span>
                </>
              )}
            </div>

            {/* The diagnosis and what was decided about it. */}
            {decision && (
              <div className="border-b border-fk-border px-5 py-4">
                <p className="text-fk-xs font-bold uppercase tracking-wider text-fk-muted">
                  Likely reason
                </p>
                <p className="mt-1 text-fk-md font-medium text-fk-ink">
                  {explanation.inference?.root_cause
                    ? humanCause(explanation.inference.root_cause)
                    : "Not diagnosed"}
                </p>
                {explanation.inference?.statement && (
                  <p className="mt-1 text-fk-sm leading-relaxed text-fk-muted">
                    {explanation.inference.statement}
                  </p>
                )}

                <div className="mt-3 rounded-[2px] border border-fk-border bg-fk-bg p-3">
                  <p className="flex items-center gap-1.5 text-fk-xs font-bold uppercase tracking-wider text-fk-muted">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Decision
                  </p>
                  {decision === "INTERVENE" && intervention ? (
                    <>
                      <p className="mt-1 text-fk-md font-medium text-fk-blue">
                        {intervention.display_name ?? humanCause(intervention.type)}
                      </p>
                      <p className="mt-1 text-fk-sm leading-relaxed text-fk-ink">
                        {intervention.reason}
                      </p>
                      <p className="mt-1.5 text-fk-xs text-fk-muted">
                        Confidence {(intervention.confidence * 100).toFixed(0)}%
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="mt-1 text-fk-md font-medium text-fk-green">
                        {decision === "ABSTAIN" ? "Holding back" : "Staying quiet"}
                      </p>
                      <p className="mt-1 text-fk-sm leading-relaxed text-fk-ink">
                        {decision === "ABSTAIN"
                          ? "The evidence did not support a confident diagnosis, so no offer was made."
                          : "This session does not need help. No nudge, no discount."}
                      </p>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* The evidence behind it, in plain language. */}
            {explanation.observations && explanation.observations.length > 0 && (
              <div className="border-b border-fk-border px-5 py-4">
                <p className="text-fk-xs font-bold uppercase tracking-wider text-fk-muted">
                  Evidence used
                </p>
                <ul className="mt-2 space-y-1.5">
                  {explanation.observations.slice(0, 4).map((item) => (
                    <li key={item.feature} className="flex gap-2 text-fk-sm text-fk-ink">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-fk-blue" />
                      {item.statement}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Raw signals still accumulating server-side. */}
            <div className="px-5 py-4">
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-[2px] border border-fk-border bg-fk-bg p-3">
                  <p className="text-fk-xs font-bold uppercase tracking-wider text-fk-muted">Cart value</p>
                  <p className="mt-1 text-fk-xl font-bold text-fk-ink">
                    ₹{(snapshot?.cart.value ?? 0).toLocaleString("en-IN")}
                  </p>
                </div>
                <div className="rounded-[2px] border border-fk-border bg-fk-bg p-3">
                  <p className="text-fk-xs font-bold uppercase tracking-wider text-fk-muted">Items</p>
                  <p className="mt-1 text-fk-xl font-bold text-fk-ink">
                    {snapshot?.cart.item_count ?? count}
                  </p>
                </div>
              </div>

              <h3 className="mb-2 mt-4 text-fk-xs font-bold uppercase tracking-wider text-fk-muted">
                Signals captured
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {counters.map(([name, value]) => (
                  <div key={name} className="rounded-[2px] border border-fk-border px-3 py-2">
                    <div className="truncate text-fk-xs text-fk-muted">{COUNTER_LABELS[name]}</div>
                    <div className="mt-0.5 text-fk-md font-bold text-fk-ink">
                      {value.toLocaleString("en-IN")}
                    </div>
                  </div>
                ))}
                {counters.length === 0 && (
                  <p className="col-span-2 rounded-[2px] border border-dashed border-fk-border p-4 text-center text-fk-sm text-fk-muted">
                    Browse a product or open reviews to start generating signals.
                  </p>
                )}
              </div>

              {latestDecision?.decision_id && (
                <Link
                  to={`/dashboard/decisions/${latestDecision.decision_id}`}
                  className="mt-4 flex items-center justify-center gap-1.5 rounded-[2px] bg-fk-blue px-4 py-3 text-fk-md font-medium text-white hover:bg-fk-blue-dark"
                >
                  Open the full decision trace
                  <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              )}
            </div>
          </div>
        </section>
      )}

      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="flex h-12 items-center gap-2 rounded-full border border-white/20 bg-fk-blue px-4 text-white shadow-[0_6px_20px_rgba(40,116,240,0.35)] transition-transform hover:-translate-y-0.5 motion-reduce:transition-none"
        aria-expanded={isOpen}
        aria-label={isOpen ? "Close assistant inspector" : "Open assistant inspector"}
      >
        <span className="relative flex h-8 w-8 items-center justify-center rounded-full bg-white/15">
          <Activity className="h-5 w-5" />
          <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-blue-600 bg-emerald-400" />
        </span>
        {displayPct !== null && (
          <span className="text-fk-md font-bold tabular-nums">{displayPct}%</span>
        )}
      </button>
    </div>
  );
}
