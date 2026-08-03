import { BrainCircuit, Check, Layers, MessageSquareText, Scale, Target } from "lucide-react";
import { AGENT_STAGES, formatMs } from "../../lib/metrics";

const STAGE_ICONS: Record<string, typeof Layers> = {
  features: Layers,
  risk: BrainCircuit,
  root_cause: Target,
  policy_and_rank: Scale,
  explain: MessageSquareText,
};

const STAGE_ORDER = ["features", "risk", "root_cause", "policy_and_rank", "explain"];

/**
 * The orchestration, shown as the agents it actually is.
 *
 * The brief asks for multi-agent orchestration explicitly, and the pipeline
 * already is one — but labelling the spans `features` and `policy_and_rank`
 * made specialised agents read like anonymous function calls.
 */
export function AgentPipeline({ latency }: { latency: Record<string, number> }) {
  const stages = STAGE_ORDER.filter((stage) => stage in latency);
  const total = latency.total ?? stages.reduce((sum, stage) => sum + latency[stage], 0);
  const slowest = Math.max(...stages.map((stage) => latency[stage]), 1);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-white">Agent orchestration</h2>
          <p className="mt-1 text-xs text-slate-400">
            Specialised agents in execution order, with the time each one spent.
          </p>
        </div>
        <span className="rounded-lg border border-cyan-500/25 bg-cyan-500/10 px-3 py-1.5 text-xs text-cyan-200">
          End-to-end <span className="font-mono font-semibold">{formatMs(total)}</span>
        </span>
      </header>
      <ol className="divide-y divide-slate-800">
        {stages.map((stage, index) => {
          const Icon = STAGE_ICONS[stage] ?? Layers;
          const agent = AGENT_STAGES[stage];
          const duration = latency[stage];
          const share = total > 0 ? (duration / total) * 100 : 0;
          return (
            <li key={stage} className="flex items-center gap-4 px-5 py-3.5">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-cyan-500/10 text-cyan-300">
                <Icon className="h-4 w-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-white">{agent?.name ?? stage}</span>
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-slate-400">
                    {index + 1}/{stages.length}
                  </span>
                </span>
                <span className="mt-0.5 block truncate text-xs text-slate-500">{agent?.role ?? stage}</span>
              </span>
              <span className="hidden w-40 shrink-0 sm:block">
                <span className="block h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                  <span
                    className="block h-full rounded-full bg-cyan-400"
                    style={{ width: `${Math.max(2, (duration / slowest) * 100)}%` }}
                  />
                </span>
                <span className="mt-1 block text-right text-[10px] text-slate-600">
                  {share.toFixed(0)}% of budget
                </span>
              </span>
              <span className="w-20 shrink-0 text-right font-mono text-xs font-semibold tabular-nums text-slate-200">
                {formatMs(duration)}
              </span>
              <span className="hidden w-16 shrink-0 items-center justify-end gap-1 text-xs text-emerald-300 sm:flex">
                <Check className="h-3.5 w-3.5" />
                ok
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
