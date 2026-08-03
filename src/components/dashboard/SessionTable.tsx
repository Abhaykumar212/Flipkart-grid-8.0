import { ArrowRight, CircleDot } from "lucide-react";
import { Link } from "react-router-dom";
import { formatProbability, formatRupees, timeAgo, titleCase } from "../../lib/metrics";
import type { ActiveSession } from "../../types/dashboard";

const DECISION_TONE: Record<string, string> = {
  INTERVENE: "bg-cyan-500/15 text-cyan-300",
  NO_ACTION: "bg-slate-700/50 text-slate-300",
  ABSTAIN: "bg-amber-500/15 text-amber-300",
};

const BAND_TONE: Record<string, string> = {
  HIGH: "bg-rose-500/15 text-rose-300",
  MEDIUM: "bg-amber-500/15 text-amber-300",
  LOW: "bg-emerald-500/15 text-emerald-300",
};

export function SessionTable({ sessions }: { sessions: ActiveSession[] }) {
  if (sessions.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/60 px-6 py-16 text-center">
        <CircleDot className="mx-auto h-8 w-8 text-slate-500" />
        <p className="mt-3 font-medium text-slate-200">No sessions match this view</p>
        <p className="mt-1 text-sm text-slate-500">
          Clear the filter, browse the storefront, or run a scenario to generate activity.
        </p>
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
            <th className="px-5 py-3 font-medium">Decision</th>
            <th className="px-5 py-3 font-medium">Risk</th>
            <th className="px-5 py-3 font-medium">Confidence</th>
            <th className="px-5 py-3" aria-label="Open" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {sessions.map((session) => {
            const decision = session.latest_decision;
            return (
              <tr key={session.session_id} className="group hover:bg-slate-800/45">
                <td className="px-5 py-4">
                  <Link
                    className="font-mono text-xs font-semibold text-cyan-300 hover:text-cyan-200"
                    to={`/dashboard/sessions/${session.session_id}`}
                  >
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
                  <p className="mt-1 text-xs text-slate-500">
                    {session.event_count} events · {session.current_route ?? "—"}
                  </p>
                </td>
                <td className="px-5 py-4 text-slate-200">
                  {formatRupees(session.cart_value)}
                  <p className="mt-1 text-xs text-slate-500">{session.item_count} items</p>
                </td>
                <td className="px-5 py-4">
                  {decision ? (
                    <Link className="block" to={`/dashboard/decisions/${decision.decision_id}`}>
                      <span
                        className={`inline-block rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
                          DECISION_TONE[decision.decision] ?? "bg-slate-700/50 text-slate-300"
                        }`}
                      >
                        {decision.decision}
                      </span>
                      <p className="mt-1.5 text-xs text-slate-300 group-hover:text-cyan-300">
                        {titleCase(decision.selected_intervention ?? "No action")}
                      </p>
                    </Link>
                  ) : (
                    <span className="text-slate-500">Awaiting decision</span>
                  )}
                </td>
                <td className="px-5 py-4">
                  {decision ? (
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        BAND_TONE[decision.risk_band] ?? "bg-slate-700/50 text-slate-300"
                      }`}
                    >
                      {formatProbability(decision.probability)} {decision.risk_band}
                    </span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
                <td className="px-5 py-4">
                  {decision && decision.confidence > 0 ? (
                    <span className="font-mono text-xs text-slate-300">
                      {(decision.confidence * 100).toFixed(0)}%
                    </span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
                <td className="px-5 py-4">
                  <Link aria-label={`Open ${session.session_id}`} to={`/dashboard/sessions/${session.session_id}`}>
                    <ArrowRight className="h-4 w-4 text-slate-600 transition group-hover:translate-x-0.5 group-hover:text-cyan-300" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
