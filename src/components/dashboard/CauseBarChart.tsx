import type { RootCauseResult } from "../../types/dashboard";

export function CauseBarChart({ causes }: { causes: RootCauseResult[] }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h2 className="text-sm font-semibold text-white">Root-cause probabilities</h2>
      <p className="mt-1 text-xs text-slate-500">Evidence-backed diagnoses ordered by confidence.</p>
      <div className="mt-5 space-y-5">
        {causes.length === 0 ? <p className="text-sm text-slate-500">Risk gate was below the cause-analysis threshold.</p> : causes.map((cause) => (
          <div key={cause.cause}>
            <div className="mb-1.5 flex items-end justify-between gap-4">
              <span className="text-xs font-medium text-slate-300">{cause.cause.replaceAll("_", " ")}</span>
              <span className="font-mono text-xs text-cyan-300">{(cause.probability * 100).toFixed(1)}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full rounded-full bg-gradient-to-r from-cyan-600 to-cyan-300" style={{ width: `${cause.probability * 100}%` }} />
            </div>
            <p className="mt-1.5 text-[11px] text-slate-500">Evidence: {cause.evidence_keys.length ? cause.evidence_keys.join(", ") : "no dominant family"}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
