import { AGENT_STAGES, formatMs } from "../../lib/metrics";
import { EmptyState, Panel } from "./Panel";
import type { LatencyPercentiles } from "../../types/dashboard";

const BUDGET_MS = 300;

/** Per-stage timings for a single decision. */
export function LatencyBreakdown({ latency }: { latency: Record<string, number> }) {
  const stages = Object.entries(latency).filter(([stage]) => stage !== "total");
  const total = latency.total ?? stages.reduce((sum, [, value]) => sum + value, 0);
  return (
    <Panel
      title="Latency breakdown"
      subtitle={`Real-time budget is ${BUDGET_MS} ms, measured before the shopper can leave.`}
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {stages.map(([stage, value]) => (
          <div key={stage} className="rounded-lg bg-slate-950/50 p-3">
            <p className="truncate text-[10px] uppercase text-slate-500" title={AGENT_STAGES[stage]?.name ?? stage}>
              {AGENT_STAGES[stage]?.name ?? stage.replaceAll("_", " ")}
            </p>
            <p className="mt-1 font-mono text-sm text-slate-200">{formatMs(value)}</p>
          </div>
        ))}
      </div>
      <div className="mt-4">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">End-to-end decision</span>
          <span className={`font-mono font-semibold ${total <= BUDGET_MS ? "text-emerald-300" : "text-amber-300"}`}>
            {formatMs(total)} / {BUDGET_MS} ms
          </span>
        </div>
        <span className="mt-2 block h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
          <span
            className={`block h-full rounded-full ${total <= BUDGET_MS ? "bg-emerald-400" : "bg-amber-400"}`}
            style={{ width: `${Math.min(100, (total / BUDGET_MS) * 100)}%` }}
          />
        </span>
      </div>
    </Panel>
  );
}

/**
 * Percentiles across every persisted decision.
 *
 * The in-process histogram resets on restart, which used to leave this panel
 * claiming 0.00 ms on a database holding hundreds of traces. These come from the
 * durable audit trail instead.
 */
export function LatencyPercentileTable({
  latency,
}: {
  latency: Record<string, LatencyPercentiles>;
}) {
  const stages = Object.entries(latency).filter(([stage]) => stage !== "total");
  const total = latency.total;

  if (stages.length === 0) {
    return (
      <Panel title="Decision latency" subtitle="Percentiles across every persisted decision.">
        <EmptyState title="No decisions recorded yet">
          Run a scenario or generate traffic from the Scenarios page to populate latency.
        </EmptyState>
      </Panel>
    );
  }

  return (
    <Panel
      title="Decision latency"
      subtitle={`Percentiles across ${total?.count.toLocaleString("en-IN") ?? 0} persisted decisions.`}
      action={
        total && (
          <span
            className={`rounded-md px-2 py-1 text-[10px] font-semibold uppercase ${
              total.p95 <= BUDGET_MS ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"
            }`}
          >
            p95 {formatMs(total.p95)}
          </span>
        )
      }
    >
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-[10px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="pb-2 pr-4 font-medium">Agent</th>
              <th className="pb-2 pr-4 text-right font-medium">p50</th>
              <th className="pb-2 pr-4 text-right font-medium">p95</th>
              <th className="pb-2 pr-4 text-right font-medium">p99</th>
              <th className="pb-2 text-right font-medium">max</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {stages.map(([stage, row]) => (
              <tr key={stage}>
                <td className="py-2.5 pr-4 text-slate-300">{AGENT_STAGES[stage]?.name ?? stage.replaceAll("_", " ")}</td>
                <td className="py-2.5 pr-4 text-right font-mono text-slate-400">{formatMs(row.p50)}</td>
                <td className="py-2.5 pr-4 text-right font-mono text-slate-200">{formatMs(row.p95)}</td>
                <td className="py-2.5 pr-4 text-right font-mono text-slate-400">{formatMs(row.p99)}</td>
                <td className="py-2.5 text-right font-mono text-slate-600">{formatMs(row.max)}</td>
              </tr>
            ))}
            {total && (
              <tr className="border-t-2 border-slate-700">
                <td className="py-2.5 pr-4 font-semibold text-white">End to end</td>
                <td className="py-2.5 pr-4 text-right font-mono text-slate-300">{formatMs(total.p50)}</td>
                <td className="py-2.5 pr-4 text-right font-mono font-semibold text-cyan-300">{formatMs(total.p95)}</td>
                <td className="py-2.5 pr-4 text-right font-mono text-slate-300">{formatMs(total.p99)}</td>
                <td className="py-2.5 text-right font-mono text-slate-600">{formatMs(total.max)}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
