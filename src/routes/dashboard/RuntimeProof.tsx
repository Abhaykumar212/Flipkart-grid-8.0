import { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  Clock3,
  Database,
  Radio,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { LatencyPercentileTable } from "../../components/dashboard/LatencyBreakdown";
import { Panel, StatTile } from "../../components/dashboard/Panel";
import { useOverview } from "../../hooks/useOverview";
import { apiGet } from "../../lib/api";
import type { RuntimeMetricsResponse } from "../../types/dashboard";

export default function RuntimeProof() {
  const [runtime, setRuntime] = useState<RuntimeMetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data: overview } = useOverview();

  useEffect(() => {
    void apiGet<RuntimeMetricsResponse>("/api/v1/metrics")
      .then(setRuntime)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Runtime metrics unavailable"));
  }, []);

  if (error) {
    return <div role="alert" className="border border-rose-400/30 bg-rose-400/10 p-5 text-sm text-rose-100">{error}</div>;
  }
  if (!runtime) return <div className="h-72 animate-pulse bg-zinc-900" />;

  const totalLatency = overview?.latency_ms.total;
  const healthyLatency = (totalLatency?.p95 ?? 0) <= 300;

  return (
    <div>
      <header className="mb-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-300">Serving evidence</p>
        <h2 className="mt-2 text-xl font-semibold text-white">Runtime health</h2>
        <p className="mt-1 text-sm text-zinc-500">Measured pipeline performance and safe-degradation signals from this process.</p>
      </header>

      <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Decision p95"
          value={totalLatency ? `${totalLatency.p95.toFixed(0)} ms` : "Unavailable"}
          tone={healthyLatency ? "good" : "warn"}
          hint="Target: under 300 ms"
        />
        <StatTile
          label="Decisions served"
          value={(overview?.decisions ?? 0).toLocaleString("en-IN")}
          hint="Since database reset"
        />
        <StatTile
          label="Live dashboard clients"
          value={runtime.gauges.sse_clients ?? 0}
          hint="Server-sent event consumers"
        />
        <StatTile
          label="Drift status"
          value={runtime.drift.drift_suspected ? "Review" : "Stable"}
          tone={runtime.drift.drift_suspected ? "warn" : "good"}
          hint={`${runtime.drift.observations} serving observations`}
        />
      </section>

      <div className="grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
        <LatencyPercentileTable latency={overview?.latency_ms ?? {}} />
        <Panel title="Reliability boundaries" subtitle="Visible safeguards on the live decision path.">
          <ul className="divide-y divide-zinc-800">
            {[
              { icon: Database, label: "Historical evidence", value: "Persisted and replayable", good: true },
              { icon: Radio, label: "Dashboard transport", value: "SSE with reconnect", good: true },
              { icon: ShieldCheck, label: "Invalid intervention", value: "Resolves to NO_ACTION", good: true },
              { icon: Activity, label: "LLM dependency", value: "Outside critical path", good: true },
              { icon: Clock3, label: "Latency budget", value: healthyLatency ? "Within target" : "Needs review", good: healthyLatency },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.label} className="flex items-center gap-3 py-3 text-xs">
                  <Icon className="h-4 w-4 shrink-0 text-zinc-500" />
                  <span className="min-w-0 flex-1 text-zinc-400">{item.label}</span>
                  <span className={`flex shrink-0 items-center gap-1.5 font-medium ${item.good ? "text-emerald-300" : "text-amber-300"}`}>
                    {item.good ? <CheckCircle2 className="h-3.5 w-3.5" /> : <TriangleAlert className="h-3.5 w-3.5" />}
                    {item.value}
                  </span>
                </li>
              );
            })}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
