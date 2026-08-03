import { useState } from "react";
import {
  Activity,
  Ban,
  Check,
  ChevronRight,
  CircleAlert,
  Clock,
  Cpu,
  FileCheck,
  Filter,
  GitBranch,
  Layers,
  ListChecks,
  ShieldCheck,
  Sparkles,
  Timer,
} from "lucide-react";
import type { PipelineRun, TraceSpan } from "../../lib/pipelineTrace";
import { STAGE_LABELS } from "../../lib/pipelineTrace";

const STAGE_ICONS: Record<string, typeof Activity> = {
  telemetry: Activity,
  feature_engineering: Layers,
  model_inference: Cpu,
  shap_attribution: Filter,
  risk_gate: Timer,
  root_cause_agent: Sparkles,
  intervention_ranking: ListChecks,
  critic_verdict: ShieldCheck,
  explanation_scored: FileCheck,
  delivery_decision: GitBranch,
};

const STATUS_STYLE: Record<string, { dot: string; text: string; bar: string; label: string }> = {
  ok: { dot: "bg-emerald-500", text: "text-emerald-700", bar: "bg-emerald-500", label: "ok" },
  running: { dot: "bg-blue-500 animate-pulse", text: "text-blue-700", bar: "bg-blue-500", label: "running" },
  skipped: { dot: "bg-slate-400", text: "text-slate-600", bar: "bg-slate-300", label: "skipped" },
  error: { dot: "bg-red-500", text: "text-red-700", bar: "bg-red-500", label: "error" },
  rate_limited: { dot: "bg-amber-500", text: "text-amber-700", bar: "bg-amber-500", label: "rate limited" },
};

function StatusIcon({ status }: { status: string }) {
  if (status === "error") return <CircleAlert className="h-3.5 w-3.5 text-red-600" />;
  if (status === "skipped") return <Ban className="h-3.5 w-3.5 text-slate-500" />;
  if (status === "rate_limited") return <Clock className="h-3.5 w-3.5 text-amber-600" />;
  return <Check className="h-3.5 w-3.5 text-emerald-600" />;
}

function SpanRow({ span, maxDuration }: { span: TraceSpan; maxDuration: number }) {
  const [open, setOpen] = useState(false);
  const style = STATUS_STYLE[span.status] ?? STATUS_STYLE.ok;
  const Icon = STAGE_ICONS[span.stage] ?? Activity;
  const widthPercent = maxDuration > 0 ? Math.max(2, (span.duration_ms / maxDuration) * 100) : 2;
  const hasDetail = Object.keys(span.detail ?? {}).length > 0;

  return (
    <li className="border-b border-slate-100 last:border-0">
      <button
        onClick={() => hasDetail && setOpen((v) => !v)}
        className={`flex w-full items-center gap-3 px-4 py-3 text-left ${hasDetail ? "hover:bg-slate-50" : "cursor-default"}`}
      >
        <ChevronRight
          className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${open ? "rotate-90" : ""} ${hasDetail ? "" : "opacity-0"}`}
        />
        <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100`}>
          <Icon className="h-4 w-4 text-slate-600" />
        </span>

        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="truncate text-sm font-medium text-slate-800">
              {STAGE_LABELS[span.stage] ?? span.stage}
            </span>
            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-500">
              {span.source}
            </span>
          </span>
          <span className="mt-0.5 block truncate text-xs text-slate-500">{span.label}</span>
        </span>

        {/* Latency bar — makes the LLM call's cost visually obvious next to the ms-scale model stages. */}
        <span className="hidden w-40 shrink-0 sm:block">
          <span className="block h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <span
              className={`block h-full rounded-full ${style.bar}`}
              style={{ width: `${widthPercent}%` }}
            />
          </span>
        </span>

        <span className="w-20 shrink-0 text-right text-xs font-semibold tabular-nums text-slate-700">
          {span.duration_ms >= 1000
            ? `${(span.duration_ms / 1000).toFixed(2)}s`
            : `${span.duration_ms.toFixed(0)}ms`}
        </span>

        <span className={`flex w-24 shrink-0 items-center justify-end gap-1 text-xs ${style.text}`}>
          <StatusIcon status={span.status} />
          {style.label}
        </span>
      </button>

      {open && hasDetail && (
        <div className="border-t border-slate-100 bg-slate-50 px-4 py-3">
          <pre className="max-h-72 overflow-auto rounded-lg bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-100">
            {JSON.stringify(span.detail, null, 2)}
          </pre>
        </div>
      )}
    </li>
  );
}

export function TraceWaterfall({ run }: { run: PipelineRun }) {
  const maxDuration = Math.max(...run.spans.map((s) => s.duration_ms), 1);

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-800">Execution trace</h2>
        <span className="text-xs text-slate-500">
          {run.spans.length} stages · click any row to inspect its payload
        </span>
      </header>
      <ol>
        {run.spans.map((span) => (
          <SpanRow key={span.id} span={span} maxDuration={maxDuration} />
        ))}
        {run.status === "running" && (
          <li className="flex items-center gap-3 px-4 py-3 text-sm text-blue-700">
            <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
            Awaiting backend response…
          </li>
        )}
      </ol>
    </section>
  );
}
