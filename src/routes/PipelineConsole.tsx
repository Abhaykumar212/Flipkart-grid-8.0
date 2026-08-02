import { Database, RefreshCw, Workflow } from "lucide-react";
import { useTracker } from "../context/TrackerContext";

export default function PipelineConsole() {
  const { snapshot, loading, error, refresh } = useTracker();
  const counters = Object.entries(snapshot?.counters ?? {}).sort(([left], [right]) => (
    left.localeCompare(right)
  ));

  return (
    <div className="flex flex-col gap-3">
      <header className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white">
            <Workflow className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-lg font-bold text-slate-900">Event pipeline console</h1>
            <p className="text-xs text-slate-500">Browser events → validated ingestion → replayable session state</p>
          </div>
          <button type="button" onClick={refresh} className="ml-auto flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </header>

      {error && (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          The event API is unavailable. Storefront interactions continue and remain buffered locally.
        </section>
      )}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_2fr]">
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-blue-600" />
            <h2 className="text-sm font-semibold text-slate-800">Canonical session</h2>
          </div>
          {snapshot ? (
            <dl className="mt-4 space-y-3 text-xs">
              <div><dt className="text-slate-500">Session ID</dt><dd className="mt-1 break-all font-mono text-slate-900">{snapshot.session.session_id}</dd></div>
              <div><dt className="text-slate-500">Route</dt><dd className="mt-1 font-semibold text-slate-900">{snapshot.session.current_route ?? "—"}</dd></div>
              <div><dt className="text-slate-500">Current product</dt><dd className="mt-1 font-semibold text-slate-900">{snapshot.session.current_product_id ?? "—"}</dd></div>
              <div><dt className="text-slate-500">Last event</dt><dd className="mt-1 font-semibold text-slate-900">{snapshot.session.last_event_at ? new Date(snapshot.session.last_event_at).toLocaleTimeString() : "—"}</dd></div>
              <div><dt className="text-slate-500">Cart</dt><dd className="mt-1 font-semibold text-slate-900">{snapshot.cart.item_count} items · ₹{snapshot.cart.value.toLocaleString("en-IN")}</dd></div>
            </dl>
          ) : (
            <p className="mt-4 text-xs text-slate-500">Waiting for the first event batch.</p>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-800">Server-side counters</h2>
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {counters.map(([name, value]) => (
              <div key={name} className="rounded-lg bg-slate-50 px-3 py-3">
                <p className="truncate text-[10px] uppercase tracking-wide text-slate-500" title={name}>{name.replaceAll("_", " ")}</p>
                <p className="mt-1 text-lg font-bold text-slate-900">{value.toLocaleString("en-IN")}</p>
              </div>
            ))}
            {counters.length === 0 && (
              <p className="col-span-full rounded-lg border border-dashed border-slate-300 p-8 text-center text-xs text-slate-500">No synchronized counters yet.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
