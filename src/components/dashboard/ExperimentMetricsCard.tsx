import type { ExperimentMetricsResponse } from "../../types/dashboard";

type Arm = ExperimentMetricsResponse["arms"][string];

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function ExperimentMetricsCard({ arm }: { arm: Arm }) {
  return (
    <article className="rounded-lg border border-slate-800 bg-slate-900 p-5">
      <h2 className="text-lg font-semibold text-white">{arm.group}</h2>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <Metric label="Sessions" value={arm.sessions} />
        <Metric label="Shown" value={arm.interventions_shown} />
        <Metric label="Conversion" value={pct(arm.conversion_rate)} />
        <Metric label="CTR" value={pct(arm.ctr)} />
        <Metric label="Dismissal" value={pct(arm.dismissal_rate)} />
        <Metric label="Margin/session" value={`₹${arm.margin_per_session.toFixed(2)}`} />
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-md bg-slate-950/60 p-3"><p className="text-[10px] uppercase text-slate-500">{label}</p><p className="mt-1 font-mono text-sm text-slate-100">{value}</p></div>;
}
