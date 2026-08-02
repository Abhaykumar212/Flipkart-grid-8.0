import type { DashboardCandidate } from "../../types/dashboard";

export function PolicyReasonList({ candidates }: { candidates: DashboardCandidate[] }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h2 className="text-sm font-semibold text-white">Policy audit</h2>
      <ol className="mt-4 space-y-3">
        {candidates.map((candidate, index) => (
          <li key={candidate.intervention} className="flex gap-3">
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-800 font-mono text-[10px] text-slate-400">{index + 1}</span>
            <div>
              <p className="text-xs font-medium text-slate-300">{candidate.intervention.replaceAll("_", " ")} <span className="text-slate-600">—</span> {candidate.policy_status}</p>
              <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                {candidate.policy_reasons.length ? candidate.policy_reasons.join(", ").replaceAll("_", " ") : "Passed every policy rule"}
                {candidate.stopped_at_rule ? ` · stopped at ${candidate.stopped_at_rule}` : ""}
                {candidate.replacement ? ` · replaced by ${candidate.replacement}` : ""}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
