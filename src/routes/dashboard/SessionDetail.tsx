import { ArrowLeft, Box, Clock3, RefreshCw, ShoppingCart } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { FeatureSnapshotGrid } from "../../components/dashboard/FeatureSnapshotGrid";
import { useSessionDetail } from "../../hooks/useSessionDetail";

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export default function SessionDetail() {
  const { sessionId = "" } = useParams();
  const { data, loading, error, refresh, stream } = useSessionDetail(sessionId);
  if (loading && !data) return <div className="h-96 animate-pulse rounded-xl bg-slate-900" />;
  if (error || !data) return <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 text-rose-200">{error ?? "Session not found"}</div>;
  return (
    <div>
      <header className="mb-7">
        <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-cyan-300"><ArrowLeft className="h-3.5 w-3.5" />All live sessions</Link>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div><p className="font-mono text-xs text-cyan-300">{data.session.session_id}</p><h1 className="mt-1 text-3xl font-semibold text-white">Session context</h1><p className="mt-2 text-sm text-slate-400">{data.session.device_type} · {data.session.referral_source} · {data.session.current_route ?? "No active route"}</p></div>
          <button onClick={() => void refresh()} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300"><span className={`h-2 w-2 rounded-full ${stream.status === "connected" ? "bg-emerald-400" : "bg-amber-400"}`} /><RefreshCw className="h-3.5 w-3.5" />Live refresh</button>
        </div>
      </header>

      <div className="grid gap-5 xl:grid-cols-[1.25fr_.75fr]">
        <section className="rounded-xl border border-slate-800 bg-slate-900">
          <header className="border-b border-slate-800 px-5 py-4"><h2 className="flex items-center gap-2 text-sm font-semibold text-white"><Clock3 className="h-4 w-4 text-cyan-300" />Event timeline</h2><p className="mt-1 text-xs text-slate-500">{data.timeline.length} immutable events in server order</p></header>
          <ol className="max-h-[650px] divide-y divide-slate-800 overflow-y-auto">
            {data.timeline.map((event) => (
              <li key={event.event_id} className="flex gap-4 px-5 py-4">
                <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-cyan-400" />
                <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-xs font-semibold text-slate-200">{event.event_type.replaceAll("_", " ")}</p><time className="font-mono text-[10px] text-slate-600">{new Date(event.server_timestamp).toLocaleTimeString()}</time></div><p className="mt-1 font-mono text-[10px] text-slate-500">seq {event.sequence_no}{event.product_id ? ` · ${event.product_id}` : ""}{event.is_late ? " · LATE" : ""}</p><details className="mt-2"><summary className="cursor-pointer text-[10px] text-slate-600 hover:text-slate-400">Inspect metadata</summary><pre className="mt-2 overflow-x-auto rounded bg-slate-950 p-2 text-[10px] text-slate-500">{JSON.stringify(event.metadata, null, 2)}</pre></details></div>
              </li>
            ))}
          </ol>
        </section>

        <div className="space-y-5">
          <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-white"><ShoppingCart className="h-4 w-4 text-cyan-300" />Current cart context</h2>
            <div className="mt-4 flex items-end justify-between border-b border-slate-800 pb-4"><div><p className="text-2xl font-semibold text-white">{currency.format(data.cart.value)}</p><p className="mt-1 text-xs text-slate-500">{data.cart.item_count} items · {currency.format(data.cart.delivery_fee)} delivery</p></div>{data.cart.promo_code && <span className="rounded bg-emerald-500/10 px-2 py-1 text-[10px] text-emerald-300">{data.cart.promo_code}</span>}</div>
            <ul className="mt-3 space-y-2">{data.cart.items.length ? data.cart.items.map((item) => <li key={`${item.product_id}-${item.variant ?? "default"}`} className="flex items-center gap-3 rounded-lg bg-slate-950/50 p-3"><Box className="h-4 w-4 shrink-0 text-slate-500" /><div className="min-w-0 flex-1"><p className="truncate text-xs text-slate-300">{item.title ?? item.product_id}</p><p className="text-[10px] text-slate-600">{item.brand} · qty {item.quantity}</p></div><span className="font-mono text-xs text-slate-400">{currency.format(item.unit_price)}</span></li>) : <li className="py-4 text-center text-xs text-slate-600">Cart has no item-level context.</li>}</ul>
          </section>
          <section className="rounded-xl border border-slate-800 bg-slate-900 p-5"><h2 className="text-sm font-semibold text-white">Decisions</h2><div className="mt-3 space-y-2">{data.decisions.length ? data.decisions.map((decision) => <Link key={decision.decision_id} to={`/dashboard/decisions/${decision.decision_id}`} className="block rounded-lg border border-slate-800 bg-slate-950/40 p-3 hover:border-cyan-500/40"><div className="flex items-center justify-between gap-3"><span className="text-xs font-medium text-slate-200">{decision.selected_intervention ?? decision.decision}</span><span className="font-mono text-xs text-cyan-300">{(decision.probability * 100).toFixed(0)}%</span></div><p className="mt-1 font-mono text-[10px] text-slate-600">{decision.decision_id}</p></Link>) : <p className="py-3 text-xs text-slate-600">No decision has run yet.</p>}</div></section>
        </div>
      </div>
      <div className="mt-5"><FeatureSnapshotGrid features={data.feature_snapshot.features} /></div>
    </div>
  );
}
