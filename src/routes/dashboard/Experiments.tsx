import { useEffect, useState } from "react";
import { ExperimentMetricsCard } from "../../components/dashboard/ExperimentMetricsCard";
import { apiGet } from "../../lib/api";
import type { ExperimentMetricsResponse } from "../../types/dashboard";

export default function Experiments() {
  const [data, setData] = useState<ExperimentMetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiGet<ExperimentMetricsResponse>("/api/v1/dashboard/experiments/EXP-001/metrics")
      .then(setData)
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Unable to load experiment metrics"));
  }, []);

  if (error) return <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-5 text-rose-200">{error}</div>;
  if (!data) return <div className="h-64 animate-pulse rounded-lg bg-slate-900" />;
  const arms = Object.values(data.arms);
  return (
    <div>
      <header className="mb-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">{data.experiment.experiment_id}</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">{data.experiment.name}</h1>
      </header>
      <section className="mb-5 rounded-lg border border-slate-800 bg-slate-900 p-5">
        <p className="text-sm text-slate-400">Uplift <span className="font-mono text-white">{(data.uplift.absolute * 100).toFixed(2)} pp</span>{data.uplift.ci95 !== null ? ` ± ${(data.uplift.ci95 * 100).toFixed(2)} pp` : ""}</p>
        <p className="mt-2 inline-flex rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-200">{data.uplift.label}</p>
      </section>
      <div className="grid gap-4 xl:grid-cols-2">
        {arms.map((arm) => <ExperimentMetricsCard key={arm.group} arm={arm} />)}
      </div>
    </div>
  );
}
