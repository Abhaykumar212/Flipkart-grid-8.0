import { NARRATIVE_LABELS } from "../../lib/featureLabels";
import { titleCase } from "../../lib/metrics";
import type { RootCauseResult } from "../../types/dashboard";

/**
 * The full ranked diagnosis, not just the winner.
 *
 * "Root Cause" is one of the four outputs the brief asks for, and a single bar
 * hides whether the model was decisive or torn between two explanations. The
 * margin between first and second is the honest signal, so it is stated.
 */
export function CauseBarChart({ causes }: { causes: RootCauseResult[] }) {
  const ranked = [...causes].sort((left, right) => right.probability - left.probability);
  const margin =
    ranked.length > 1 ? ranked[0].probability - ranked[1].probability : ranked[0]?.probability ?? 0;

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-white">Root-cause probabilities</h2>
          <p className="mt-1 text-xs text-slate-500">Evidence-backed diagnoses ordered by confidence.</p>
        </div>
        {ranked.length > 0 && (
          <span
            className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
              margin >= 0.2
                ? "bg-emerald-500/15 text-emerald-300"
                : "bg-amber-500/15 text-amber-300"
            }`}
          >
            {margin >= 0.2 ? "decisive" : "close call"} · margin {(margin * 100).toFixed(0)}pp
          </span>
        )}
      </div>

      <div className="mt-5 space-y-5">
        {ranked.length === 0 ? (
          <p className="text-sm text-slate-500">
            Risk sat below the cause-analysis threshold, so no diagnosis was attempted.
          </p>
        ) : (
          ranked.map((cause, index) => (
            <div key={cause.cause}>
              <div className="mb-1.5 flex items-end justify-between gap-4">
                <span
                  className={`text-xs font-medium ${index === 0 ? "text-white" : "text-slate-400"}`}
                >
                  {index === 0 && <span className="mr-1.5 text-cyan-300">▸</span>}
                  {titleCase(cause.cause)}
                </span>
                <span className="font-mono text-xs text-cyan-300">
                  {(cause.probability * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full ${
                    index === 0
                      ? "bg-gradient-to-r from-cyan-600 to-cyan-300"
                      : "bg-slate-600"
                  }`}
                  style={{ width: `${Math.max(1, cause.probability * 100)}%` }}
                />
              </div>
              <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500">
                {cause.evidence_keys.length
                  ? `Evidence: ${cause.evidence_keys
                      .map((key) => NARRATIVE_LABELS[key] ?? titleCase(key))
                      .join(" · ")}`
                  : "No dominant evidence family."}
              </p>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
