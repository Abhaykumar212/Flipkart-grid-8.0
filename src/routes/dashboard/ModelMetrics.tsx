import { useEffect, useState } from "react";
import { ChevronDown, TriangleAlert } from "lucide-react";
import { ModelCard } from "../../components/dashboard/ModelCard";
import { LatencyPercentileTable } from "../../components/dashboard/LatencyBreakdown";
import { PageHeader, Panel, StatTile } from "../../components/dashboard/Panel";
import { apiGet } from "../../lib/api";
import { formatPercent } from "../../lib/metrics";
import { useOverview } from "../../hooks/useOverview";
import type { ModelMetricsResponse, RuntimeMetricsResponse } from "../../types/dashboard";

export default function ModelMetrics({ embedded = false }: { embedded?: boolean }) {
  const [data, setData] = useState<ModelMetricsResponse | null>(null);
  const [runtime, setRuntime] = useState<RuntimeMetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showShadow, setShowShadow] = useState(false);
  const { data: overview } = useOverview();

  useEffect(() => {
    void Promise.all([
      apiGet<ModelMetricsResponse>("/api/v1/dashboard/metrics"),
      apiGet<RuntimeMetricsResponse>("/api/v1/metrics"),
    ])
      .then(([models, runtimeMetrics]) => {
        setData(models);
        setRuntime(runtimeMetrics);
      })
      .catch((requestError) =>
        setError(requestError instanceof Error ? requestError.message : "Unable to load metrics"),
      );
  }, []);

  if (error) {
    return (
      <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-5 text-rose-200">
        {error}
      </div>
    );
  }
  if (!data || !runtime) return <div className="h-64 animate-pulse rounded-lg bg-slate-900" />;

  const evaluated = data.models.filter((model) => Object.keys(model.metrics ?? {}).length > 0);
  const registryOnly = data.models.filter((model) => Object.keys(model.metrics ?? {}).length === 0);

  return (
    <div>
      <PageHeader
        eyebrow={embedded ? undefined : "Model registry"}
        title={embedded ? "Serving model evidence" : "Model metrics"}
        description="Held-out results for the models currently serving decisions, plus what the decision path actually cost at runtime."
      />

      <div className="mb-5 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
        <p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-amber-300">
          <TriangleAlert className="h-3.5 w-3.5" />
          Synthetic holdout
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-amber-100/70">
          These are results on a synthetic holdout from the behavioural simulator, not production
          performance. They establish that the pipeline trains, calibrates, and serves correctly —
          nothing more.
        </p>
      </div>

      {overview && overview.decisions > 0 && (
        <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatTile
            label="Decisions served"
            value={overview.decisions.toLocaleString("en-IN")}
            hint="Since the last database reset"
          />
          <StatTile
            label="Mean predicted risk"
            value={overview.mean_probability === null ? "—" : formatPercent(overview.mean_probability, 1)}
          />
          <StatTile
            label="Mean confidence"
            value={overview.mean_confidence === null ? "—" : formatPercent(overview.mean_confidence, 1)}
          />
          <StatTile
            label="Abstained"
            value={overview.by_decision.ABSTAIN ?? 0}
            hint="Cause evidence too weak to act on"
          />
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        {evaluated.map((model) => (
          <ModelCard key={model.model_id} model={model} />
        ))}
      </div>

      {registryOnly.length > 0 && (
        <div className="mt-4">
          <button
            type="button"
            onClick={() => setShowShadow((value) => !value)}
            aria-expanded={showShadow}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-400 hover:text-white"
          >
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${showShadow ? "rotate-180" : ""}`} />
            {registryOnly.length} registered version{registryOnly.length === 1 ? "" : "s"} kept for rollback
          </button>
          {showShadow && (
            <div className="mt-3 grid gap-4 xl:grid-cols-2">
              {registryOnly.map((model) => (
                <ModelCard key={model.model_id} model={model} />
              ))}
            </div>
          )}
        </div>
      )}

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <LatencyPercentileTable latency={overview?.latency_ms ?? {}} />
        <Panel
          title="Drift monitor"
          subtitle="Report-only PSI over the serving feature distribution."
          action={
            <span
              className={`rounded-md px-2 py-1 text-[10px] font-semibold uppercase ${
                runtime.drift.drift_suspected
                  ? "bg-amber-500/15 text-amber-300"
                  : "bg-emerald-500/15 text-emerald-300"
              }`}
            >
              {runtime.drift.drift_suspected ? "Review" : "Stable"}
            </span>
          }
        >
          <dl className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-slate-950/50 p-3">
              <dt className="text-slate-500">Observed this process</dt>
              <dd className="mt-1 font-mono text-white">{runtime.drift.observations}</dd>
            </div>
            <div className="rounded-lg bg-slate-950/50 p-3">
              <dt className="text-slate-500">Mean risk</dt>
              <dd className="mt-1 font-mono text-white">
                {runtime.drift.mean_predicted_probability?.toFixed(3) ?? "—"}
              </dd>
            </div>
            <div className="rounded-lg bg-slate-950/50 p-3">
              <dt className="text-slate-500">Dashboard clients</dt>
              <dd className="mt-1 font-mono text-white">{runtime.gauges.sse_clients ?? 0}</dd>
            </div>
            <div className="rounded-lg bg-slate-950/50 p-3">
              <dt className="text-slate-500">Automated rollback</dt>
              <dd className="mt-1 font-mono text-white">Disabled</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs leading-relaxed text-slate-500">
            {runtime.drift.baseline_available
              ? "Drift is reported for human review only; the system never swaps a model on its own."
              : "A PSI baseline is written with the next training run."}
          </p>
        </Panel>
      </div>
    </div>
  );
}
