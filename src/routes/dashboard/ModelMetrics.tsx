import { useEffect, useState } from "react";
import { ModelCard } from "../../components/dashboard/ModelCard";
import { LatencyBreakdown } from "../../components/dashboard/LatencyBreakdown";
import { apiGet } from "../../lib/api";
import type { ModelMetricsResponse, RuntimeMetricsResponse } from "../../types/dashboard";

export default function ModelMetrics() {
  const [data, setData] = useState<ModelMetricsResponse | null>(null);
  const [runtime, setRuntime] = useState<RuntimeMetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      apiGet<ModelMetricsResponse>("/api/v1/dashboard/metrics"),
      apiGet<RuntimeMetricsResponse>("/api/v1/metrics"),
    ])
      .then(([models, runtimeMetrics]) => { setData(models); setRuntime(runtimeMetrics); })
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Unable to load metrics"));
  }, []);

  if (error) return <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-5 text-rose-200">{error}</div>;
  if (!data || !runtime) return <div className="h-64 animate-pulse rounded-lg bg-slate-900" />;
  const p95Latency = Object.fromEntries(
    Object.entries(runtime.latency_ms)
      .filter(([name]) => name.startsWith("decision_"))
      .map(([name, histogram]) => [name.replace("decision_", ""), histogram.p95]),
  );
  return (
    <div>
      <header className="mb-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">View 14</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Model metrics</h1>
      </header>
      <div className="grid gap-4 xl:grid-cols-2">
        {data.models.map((model) => <ModelCard key={model.model_id} model={model} />)}
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <LatencyBreakdown latency={p95Latency} />
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-white">Drift monitor</h2>
            <span className={`rounded-md px-2 py-1 text-[10px] ${runtime.drift.drift_suspected ? "bg-amber-500/15 text-amber-300" : "bg-emerald-500/15 text-emerald-300"}`}>
              {runtime.drift.drift_suspected ? "Review" : "Stable"}
            </span>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-slate-950/50 p-3"><dt className="text-slate-500">Decisions observed</dt><dd className="mt-1 font-mono text-white">{runtime.drift.observations}</dd></div>
            <div className="rounded-lg bg-slate-950/50 p-3"><dt className="text-slate-500">Mean risk</dt><dd className="mt-1 font-mono text-white">{runtime.drift.mean_predicted_probability?.toFixed(3) ?? "—"}</dd></div>
            <div className="rounded-lg bg-slate-950/50 p-3"><dt className="text-slate-500">SSE clients</dt><dd className="mt-1 font-mono text-white">{runtime.gauges.sse_clients ?? 0}</dd></div>
            <div className="rounded-lg bg-slate-950/50 p-3"><dt className="text-slate-500">Automated action</dt><dd className="mt-1 font-mono text-white">Disabled</dd></div>
          </dl>
          {!runtime.drift.baseline_available && <p className="mt-3 text-xs text-slate-500">PSI baseline is written with the next model training run.</p>}
        </section>
      </div>
    </div>
  );
}
