import { useState } from "react";
import { Activity, RefreshCw, Workflow, X } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useCart } from "../../context/CartContext";
import { useTracker } from "../../context/TrackerContext";

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

export function AgentInspector() {
  const [isOpen, setIsOpen] = useState(false);
  const { pathname } = useLocation();
  const { count } = useCart();
  const { snapshot, loading, error, refresh } = useTracker();

  if (count === 0 && (snapshot?.cart.item_count ?? 0) === 0) return null;

  const counters = Object.entries(snapshot?.counters ?? {})
    .filter(([name]) => name in COUNTER_LABELS)
    .sort(([left], [right]) => left.localeCompare(right));
  const eventCount = Object.values(snapshot?.counters ?? {}).reduce(
    (total, value) => total + value,
    0,
  );
  const clearsMobileCheckoutBar = pathname === "/cart" || pathname === "/checkout";
  const status = loading ? "Syncing" : snapshot ? `${eventCount} signals` : "Buffering";

  return (
    <div className={`fixed right-3 z-[9999] lg:bottom-5 lg:right-5 ${clearsMobileCheckoutBar ? "bottom-[calc(5.25rem+env(safe-area-inset-bottom))]" : "bottom-3"}`}>
      {isOpen && (
        <section className="absolute bottom-16 right-0 flex max-h-[min(72vh,680px)] w-[min(430px,calc(100vw-24px))] flex-col overflow-hidden rounded-[2px] border border-slate-200 bg-white shadow-[0_24px_70px_rgba(15,23,42,0.28)]">
          <header className="bg-fk-footer px-5 py-4 text-white">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-bold">Live session inspector</h2>
                <p className="text-[11px] text-slate-400">Backend-owned counters · replayable events</p>
              </div>
              <div className="flex items-center gap-1">
                <Link to="/pipeline" onClick={() => setIsOpen(false)} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white" aria-label="Open pipeline console">
                  <Workflow className="h-4 w-4" />
                </Link>
                <button type="button" onClick={refresh} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white" aria-label="Refresh session">
                  <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                </button>
                <button type="button" onClick={() => setIsOpen(false)} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white" aria-label="Close session inspector">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <p className="mt-3 truncate rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-blue-200">
              {snapshot?.session.session_id ?? "Waiting for the event API"}
            </p>
          </header>

          <div className="overflow-y-auto p-5">
            {error && (
              <p className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                Events remain buffered while the API is unavailable.
              </p>
            )}
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Cart value</p>
                <p className="mt-1 text-xl font-black text-slate-900">₹{(snapshot?.cart.value ?? 0).toLocaleString("en-IN")}</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Items</p>
                <p className="mt-1 text-xl font-black text-slate-900">{snapshot?.cart.item_count ?? count}</p>
              </div>
            </div>

            <h3 className="mb-2 mt-5 text-[11px] font-bold uppercase tracking-wider text-slate-500">Session counters</h3>
            <div className="grid grid-cols-2 gap-2">
              {counters.map(([name, value]) => (
                <div key={name} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
                  <div className="truncate text-[10px] text-slate-500">{COUNTER_LABELS[name]}</div>
                  <div className="mt-0.5 text-sm font-bold text-slate-900">{value.toLocaleString("en-IN")}</div>
                </div>
              ))}
              {counters.length === 0 && (
                <p className="col-span-2 rounded-xl border border-dashed border-slate-300 p-4 text-center text-xs text-slate-500">Waiting for the first batch to sync.</p>
              )}
            </div>
          </div>
        </section>
      )}

      <button type="button" onClick={() => setIsOpen((open) => !open)} className="flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-fk-blue text-white shadow-[0_6px_20px_rgba(40,116,240,0.35)] transition-transform hover:-translate-y-0.5 motion-reduce:transition-none" aria-expanded={isOpen} aria-label={isOpen ? "Close session inspector" : "Open session inspector"} title={`Session inspector · ${status}`}>
        <span className="relative flex h-8 w-8 items-center justify-center rounded-full bg-white/15">
          <Activity className="h-5 w-5" />
          <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-blue-600 bg-emerald-400" />
        </span>
      </button>
    </div>
  );
}
