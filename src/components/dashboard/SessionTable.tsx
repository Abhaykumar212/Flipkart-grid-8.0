import { ArrowRight, CircleDot } from "lucide-react";
import { Link } from "react-router-dom";
import type { ActiveSession } from "../../types/dashboard";

const currency = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function timeAgo(value: string | null): string {
  if (!value) return "No events yet";
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1_000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3_600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3_600)}h ago`;
}

export function SessionTable({ sessions }: { sessions: ActiveSession[] }) {
  if (sessions.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/60 px-6 py-16 text-center">
        <CircleDot className="mx-auto h-8 w-8 text-slate-500" />
        <p className="mt-3 font-medium text-slate-200">No active shopping sessions</p>
        <p className="mt-1 text-sm text-slate-500">New storefront activity will appear here live.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/80 shadow-2xl shadow-black/10">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-800 bg-slate-950/60 text-xs uppercase tracking-wider text-slate-500">
          <tr>
            <th className="px-5 py-3 font-medium">Session</th>
            <th className="px-5 py-3 font-medium">Activity</th>
            <th className="px-5 py-3 font-medium">Cart</th>
            <th className="px-5 py-3 font-medium">Latest decision</th>
            <th className="px-5 py-3 font-medium">Risk</th>
            <th className="px-5 py-3" aria-label="Open" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {sessions.map((session) => (
            <tr key={session.session_id} className="group hover:bg-slate-800/45">
              <td className="px-5 py-4">
                <Link className="font-mono text-xs font-semibold text-cyan-300 hover:text-cyan-200" to={`/dashboard/sessions/${session.session_id}`}>
                  {session.session_id}
                </Link>
                <p className="mt-1 text-xs text-slate-500">
                  {session.device_type ?? "Unknown"} · {session.referral_source ?? "Direct"}
                </p>
              </td>
              <td className="px-5 py-4">
                <span className="inline-flex items-center gap-1.5 text-emerald-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  {timeAgo(session.last_event_at)}
                </span>
                <p className="mt-1 text-xs text-slate-500">{session.event_count} events · {session.current_route ?? "—"}</p>
              </td>
              <td className="px-5 py-4 text-slate-200">
                {currency.format(session.cart_value)}
                <p className="mt-1 text-xs text-slate-500">{session.item_count} items</p>
              </td>
              <td className="px-5 py-4">
                {session.latest_decision ? (
                  <Link className="text-slate-200 hover:text-cyan-300" to={`/dashboard/decisions/${session.latest_decision.decision_id}`}>
                    {session.latest_decision.selected_intervention ?? session.latest_decision.decision}
                    <p className="mt-1 font-mono text-[11px] text-slate-500">{session.latest_decision.decision_id}</p>
                  </Link>
                ) : <span className="text-slate-500">Awaiting decision</span>}
              </td>
              <td className="px-5 py-4">
                {session.latest_decision ? (
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${session.latest_decision.risk_band === "HIGH" ? "bg-rose-500/15 text-rose-300" : session.latest_decision.risk_band === "MEDIUM" ? "bg-amber-500/15 text-amber-300" : "bg-emerald-500/15 text-emerald-300"}`}>
                    {(session.latest_decision.probability * 100).toFixed(0)}% {session.latest_decision.risk_band}
                  </span>
                ) : <span className="text-slate-600">—</span>}
              </td>
              <td className="px-5 py-4">
                <Link aria-label={`Open ${session.session_id}`} to={`/dashboard/sessions/${session.session_id}`}>
                  <ArrowRight className="h-4 w-4 text-slate-600 transition group-hover:translate-x-0.5 group-hover:text-cyan-300" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
