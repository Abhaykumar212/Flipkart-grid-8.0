import { CheckCircle2, CircleX, GitBranch } from "lucide-react";
import type { DashboardCandidate } from "../../types/dashboard";

function PolicyBadge({ status }: { status: string }) {
  const pass = status === "PASS";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold ${pass ? "bg-emerald-500/15 text-emerald-300" : status === "DOWNGRADE" ? "bg-amber-500/15 text-amber-300" : "bg-rose-500/15 text-rose-300"}`}>
      {pass ? <CheckCircle2 className="h-3 w-3" /> : <CircleX className="h-3 w-3" />}{status.replaceAll("_", " ")}
    </span>
  );
}

export function CandidateTable({ candidates }: { candidates: DashboardCandidate[] }) {
  return (
    <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
      <header className="border-b border-slate-800 px-5 py-4">
        <h2 className="text-sm font-semibold text-white">Candidate interventions</h2>
        <p className="mt-1 text-xs text-slate-500">Every considered action, policy result, and rejection reason—including the discount counterfactual.</p>
      </header>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="bg-slate-950/50 uppercase tracking-wider text-slate-500">
            <tr><th className="px-4 py-3">Candidate</th><th className="px-4 py-3">Policy</th><th className="px-4 py-3">Reasons</th><th className="px-4 py-3 text-right">Utility</th><th className="px-4 py-3">Channel</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {candidates.map((candidate) => (
              <tr key={candidate.intervention} className={candidate.selected ? "bg-cyan-500/5" : ""}>
                <td className="px-4 py-4">
                  <span className="flex items-center gap-2 font-semibold text-slate-200">
                    {candidate.selected && <GitBranch className="h-3.5 w-3.5 text-cyan-300" />}{candidate.display_name}
                  </span>
                  <span className="mt-1 block font-mono text-[10px] text-slate-500">{candidate.intervention} · {candidate.cost_level ?? "—"} COST{!candidate.generated ? " · COUNTERFACTUAL" : ""}</span>
                </td>
                <td className="px-4 py-4"><PolicyBadge status={candidate.policy_status} /></td>
                <td className="max-w-sm px-4 py-4 text-slate-400">
                  <details>
                    <summary className="cursor-pointer">{candidate.policy_reasons.length ? `${candidate.policy_reasons.length} policy reason(s)` : "All checks passed"}</summary>
                    <p className="mt-1">{candidate.policy_reasons.length ? candidate.policy_reasons.map((reason) => reason.replaceAll("_", " ")).join("; ") : "All ordered policy checks passed"}</p>
                    {candidate.explanation && <p className="mt-1 text-[11px] text-slate-500">{candidate.explanation}</p>}
                  </details>
                </td>
                <td className="px-4 py-4 text-right font-mono font-semibold text-slate-200">{candidate.utility_score?.toFixed(3) ?? "—"}</td>
                <td className="px-4 py-4 text-slate-400">{candidate.channel?.replaceAll("_", " ") ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
