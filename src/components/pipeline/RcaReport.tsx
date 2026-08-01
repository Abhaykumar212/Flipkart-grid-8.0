import { AlertTriangle, Ban, Quote, Target, TrendingUp } from "lucide-react";
import type { PipelineRun } from "../../lib/pipelineTrace";

const CATEGORY_STYLE: Record<string, { label: string; chip: string }> = {
  cost_friction: { label: "Cost friction", chip: "bg-rose-100 text-rose-700" },
  delivery_friction: { label: "Delivery friction", chip: "bg-sky-100 text-sky-700" },
  trust_friction: { label: "Trust friction", chip: "bg-amber-100 text-amber-700" },
  checkout_friction: { label: "Checkout friction", chip: "bg-fuchsia-100 text-fuchsia-700" },
  product_uncertainty: { label: "Product uncertainty", chip: "bg-teal-100 text-teal-700" },
  low_intent: { label: "Low intent", chip: "bg-slate-100 text-slate-700" },
};

const CONFIDENCE_STYLE: Record<string, string> = {
  high: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-slate-100 text-slate-600",
};

/** Explains why the pipeline stopped early, rather than showing an empty panel. */
function GateHeldNotice({ run }: { run: PipelineRun }) {
  const messages: Record<string, { title: string; tone: string }> = {
    gate_not_met: {
      title: "Trigger policy withheld the analysis",
      tone: "border-emerald-200 bg-emerald-50 text-emerald-900",
    },
    not_configured: {
      title: "Root cause agent is not configured",
      tone: "border-amber-200 bg-amber-50 text-amber-900",
    },
    rate_limited: {
      title: "Model provider rate limit reached",
      tone: "border-amber-200 bg-amber-50 text-amber-900",
    },
    error: {
      title: "Analysis failed",
      tone: "border-red-200 bg-red-50 text-red-900",
    },
  };
  const info = messages[run.status] ?? messages.error;

  return (
    <section className={`rounded-xl border p-5 ${info.tone}`}>
      <h2 className="flex items-center gap-2 text-sm font-semibold">
        <Ban className="h-4 w-4" />
        {info.title}
      </h2>
      <p className="mt-2 text-sm">{run.gate?.reason ?? run.message}</p>
      {run.status === "gate_not_met" && (
        <p className="mt-3 text-xs opacity-80">
          No LLM call was made. The agent only runs above the{" "}
          {run.gate ? `${(run.gate.threshold * 100).toFixed(0)}%` : "high-risk"} threshold, where the
          model's holdout precision is 90%, so intervention budget is spent only where it pays.
        </p>
      )}
      {run.gate && Object.keys(run.gate.checks).length > 0 && (
        <pre className="mt-3 overflow-auto rounded-lg bg-white/60 p-3 text-[11px] text-slate-700">
          {JSON.stringify(run.gate.checks, null, 2)}
        </pre>
      )}
    </section>
  );
}

export function RcaReport({ run }: { run: PipelineRun }) {
  if (run.status === "running") {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-8 text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
        <p className="mt-3 text-sm text-slate-600">Running pipeline…</p>
      </section>
    );
  }

  if (!run.analysis) return <GateHeldNotice run={run} />;

  const { analysis } = run;
  const cause = analysis.primary_root_cause;
  const style = CATEGORY_STYLE[cause.category] ?? CATEGORY_STYLE.low_intent;
  const maxShap = Math.max(
    ...cause.supporting_evidence.map((e) => Math.abs(e.shap_contribution)),
    0.0001,
  );

  return (
    <div className="flex flex-col gap-3">
      {/* Primary cause */}
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${style.chip}`}>
            {style.label}
          </span>
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-semibold ${CONFIDENCE_STYLE[analysis.confidence]}`}
          >
            {analysis.confidence} confidence
          </span>
          {run.modelUsed && (
            <span className="ml-auto text-xs text-slate-500">
              {run.modelUsed} · {(run.llmLatencyMs / 1000).toFixed(2)}s
            </span>
          )}
        </div>

        <h2 className="mt-3 text-lg font-bold text-slate-900">{cause.headline}</h2>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-700">{cause.explanation}</p>
        <p className="mt-2 text-xs italic text-slate-500">{analysis.confidence_reasoning}</p>
      </section>

      {/* Evidence — the SHAP grounding */}
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800">
          <Target className="h-4 w-4 text-slate-500" />
          Evidence from the model's own attribution
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          Each item is a SHAP value the XGBoost model produced — the agent explains these, it does
          not invent them.
        </p>
        <ul className="mt-3 flex flex-col gap-3">
          {cause.supporting_evidence.map((item, i) => (
            <li key={`${item.signal}-${i}`} className="rounded-lg border border-slate-100 p-3">
              <div className="flex flex-wrap items-baseline gap-2">
                <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-800">
                  {item.signal}
                </code>
                <span className="text-sm font-medium text-slate-900">{item.observed_value}</span>
                <span
                  className={`ml-auto text-xs font-bold tabular-nums ${item.shap_contribution >= 0 ? "text-red-600" : "text-emerald-600"}`}
                >
                  SHAP {item.shap_contribution >= 0 ? "+" : ""}
                  {item.shap_contribution.toFixed(3)}
                </span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full ${item.shap_contribution >= 0 ? "bg-red-500" : "bg-emerald-500"}`}
                  style={{ width: `${(Math.abs(item.shap_contribution) / maxShap) * 100}%` }}
                />
              </div>
              <p className="mt-1.5 text-xs text-slate-600">{item.why_it_matters}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* Narrative */}
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800">
          <Quote className="h-4 w-4 text-slate-500" />
          What's happening, in plain English
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-700">{analysis.shopper_narrative}</p>

        {analysis.contributing_factors.length > 0 && (
          <div className="mt-4 border-t border-slate-100 pt-3">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Also contributing
            </h4>
            <ul className="mt-2 flex flex-col gap-1.5">
              {analysis.contributing_factors.map((factor, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span
                    className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold ${(CATEGORY_STYLE[factor.category] ?? CATEGORY_STYLE.low_intent).chip}`}
                  >
                    {(CATEGORY_STYLE[factor.category] ?? CATEGORY_STYLE.low_intent).label}
                  </span>
                  <span>
                    {factor.headline}{" "}
                    <code className="text-xs text-slate-500">({factor.signal})</code>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Levers — the Phase 3 handoff */}
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800">
          <TrendingUp className="h-4 w-4 text-slate-500" />
          Recommended interventions
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          Chosen from a closed catalog, so the next stage receives an executable instruction rather
          than free text.
        </p>

        <ol className="mt-3 flex flex-col gap-2">
          {[...analysis.recommended_levers]
            .sort((a, b) => a.priority - b.priority)
            .map((lever) => (
              <li
                key={lever.lever_id}
                className="flex gap-3 rounded-lg border border-emerald-100 bg-emerald-50/60 p-3"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-xs font-bold text-white">
                  {lever.priority}
                </span>
                <div className="min-w-0">
                  <code className="text-sm font-semibold text-emerald-900">{lever.lever_id}</code>
                  <p className="mt-0.5 text-xs text-slate-700">{lever.rationale}</p>
                  <p className="mt-1 text-xs font-medium text-emerald-800">
                    Expected: {lever.expected_effect}
                  </p>
                </div>
              </li>
            ))}
        </ol>

        {analysis.levers_to_avoid.length > 0 && (
          <div className="mt-4 border-t border-slate-100 pt-3">
            <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <AlertTriangle className="h-3.5 w-3.5" />
              Deliberately not recommended
            </h4>
            <p className="mt-1 text-[11px] text-slate-500">
              Protects margin — the agent flags levers that would be wasted spend on this shopper.
            </p>
            <ul className="mt-2 flex flex-col gap-1.5">
              {analysis.levers_to_avoid.map((lever) => (
                <li key={lever.lever_id} className="flex gap-2 text-sm text-slate-600">
                  <Ban className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
                  <span>
                    <code className="text-xs font-semibold text-slate-700">{lever.lever_id}</code> —{" "}
                    {lever.reason}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
