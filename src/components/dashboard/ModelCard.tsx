import { METRIC_GUIDE, formatMetric } from "../../lib/metrics";
import type { ModelMetricsResponse } from "../../types/dashboard";

type Model = ModelMetricsResponse["models"][number];

const STATUS_TONE: Record<string, string> = {
  ACTIVE: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  SHADOW: "border-slate-700 bg-slate-800 text-slate-400",
  RETIRED: "border-slate-800 bg-slate-900 text-slate-600",
};

/**
 * One registered model, with its metrics explained.
 *
 * Metrics used to render at full float precision, which is unreadable and hides
 * the more useful question of what each number means and which direction is
 * good. Anything without a guide entry is still shown, just unannotated.
 */
export function ModelCard({ model }: { model: Model }) {
  // Training writes placeholder keys for artifacts it did not produce, and the
  // model name and version are already in the header. Rendering either as an
  // empty tile makes a complete card look half-finished.
  const redundant = new Set(["model_name", "model_version"]);
  const entries = Object.entries(model.metrics ?? {}).filter(
    ([name, value]) =>
      !redundant.has(name)
      && value !== null
      && value !== undefined
      && value !== ""
      && !(Array.isArray(value) && value.length === 0)
      && !(typeof value === "object" && Object.keys(value as object).length === 0),
  );

  return (
    <article className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            {model.model_type.replaceAll("_", " ")}
          </p>
          <h2 className="mt-1 text-base font-semibold text-white">{model.model_name}</h2>
          <p className="mt-1 font-mono text-xs text-cyan-300">{model.model_version}</p>
        </div>
        <span
          className={`shrink-0 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase ${
            STATUS_TONE[model.status] ?? "border-slate-700 text-slate-300"
          }`}
        >
          {model.status}
        </span>
      </div>

      {entries.length === 0 ? (
        <p className="mt-4 rounded-lg border border-dashed border-slate-800 p-4 text-center text-xs text-slate-600">
          Registered for rollback. No evaluation metrics recorded for this version.
        </p>
      ) : (
        <dl className="mt-4 grid gap-2 sm:grid-cols-2">
          {entries.map(([name, value]) => {
            const guide = METRIC_GUIDE[name];
            return (
              <div key={name} className="rounded-lg bg-slate-950/60 p-3">
                <dt className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                  {guide?.label ?? name.replaceAll("_", " ")}
                </dt>
                <dd className="mt-1 font-mono text-sm font-semibold text-slate-100">
                  {formatMetric(value as number | string | boolean)}
                </dd>
                {guide && (
                  <p className="mt-1.5 text-[10px] leading-snug text-slate-600">{guide.hint}</p>
                )}
              </div>
            );
          })}
        </dl>
      )}

      <p className="mt-4 flex flex-wrap gap-x-3 text-[11px] text-slate-500">
        <span>Trained {new Date(model.trained_at).toLocaleString()}</span>
        <span className="font-mono text-slate-600">{model.feature_schema_version}</span>
      </p>
    </article>
  );
}
