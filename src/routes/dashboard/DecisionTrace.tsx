import { ArrowLeft, CheckCircle2, RefreshCw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { CandidateTable } from "../../components/dashboard/CandidateTable";
import { CauseBarChart } from "../../components/dashboard/CauseBarChart";
import { ExplanationTrail } from "../../components/dashboard/ExplanationTrail";
import { LatencyBreakdown } from "../../components/dashboard/LatencyBreakdown";
import { PolicyReasonList } from "../../components/dashboard/PolicyReasonList";
import { RiskGauge } from "../../components/dashboard/RiskGauge";
import { UtilityBreakdownChart } from "../../components/dashboard/UtilityBreakdownChart";
import { TraceWaterfall } from "../../components/pipeline/TraceWaterfall";
import { useDecisionTrace } from "../../hooks/useDecisionTrace";
import type { PipelineRun, TraceSpan } from "../../lib/pipelineTrace";
import type { DecisionTraceResponse } from "../../types/dashboard";

function pipelineRun(trace: DecisionTraceResponse): PipelineRun {
  const startedAt = new Date(trace.decision_time).getTime() - (trace.latency_ms.total ?? 0);
  let cursor = startedAt;
  const label: Record<string, string> = { features: "Compute canonical feature vector", risk: "Predict abandonment risk", root_cause: "Infer supported root causes", policy_and_rank: "Apply policy and rank utility", explain: "Build grounded explanation" };
  const spans: TraceSpan[] = Object.entries(trace.latency_ms).filter(([stage]) => stage !== "total").map(([stage, duration]) => {
    const span = { id: `${trace.trace_id}-${stage}`, stage, label: label[stage] ?? stage, status: "ok" as const, started_at: cursor, duration_ms: duration, source: "backend" as const, detail: {} };
    cursor += duration;
    return span;
  });
  return { id: trace.trace_id, startedAt, status: "success", trigger: "auto", probability: trace.risk.probability, riskTier: trace.risk.band, gate: null, analysis: null, modelUsed: trace.risk.model_version, llmLatencyMs: 0, message: null, spans };
}

export default function DecisionTrace() {
  const { decisionId = "" } = useParams();
  const { data, loading, error, refresh, stream } = useDecisionTrace(decisionId);
  if (loading && !data) return <div className="h-96 animate-pulse rounded-xl bg-slate-900" />;
  if (error || !data) return <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 text-rose-200">{error ?? "Decision not found"}</div>;
  const winner = data.utility_scores.find((item) => item.intervention === data.final.selected_intervention) ?? data.utility_scores[0];
  const runnerUp = data.utility_scores.find((item) => item.intervention !== winner?.intervention);
  return (
    <div>
      <header className="mb-7">
        <Link to={`/dashboard/sessions/${data.session_id}`} className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-cyan-300"><ArrowLeft className="h-3.5 w-3.5" />Session {data.session_id}</Link>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div><p className="font-mono text-xs text-cyan-300">{data.decision_id}</p><h1 className="mt-1 text-3xl font-semibold text-white">Full decision trace</h1><p className="mt-2 text-sm text-slate-400">Triggered by {data.trigger.replaceAll("_", " ")} · {new Date(data.decision_time).toLocaleString()}</p></div>
          <button onClick={() => void refresh()} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300"><span className={`h-2 w-2 rounded-full ${stream.status === "connected" ? "bg-emerald-400" : "bg-amber-400"}`} /><RefreshCw className="h-3.5 w-3.5" />Live</button>
        </div>
      </header>

      <section className="mb-5 flex flex-wrap items-center justify-between gap-5 rounded-xl border border-cyan-500/25 bg-gradient-to-r from-cyan-500/10 to-slate-900 p-5">
        <div><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">Final recommendation</p><p className="mt-2 text-2xl font-semibold text-white">{(data.final.selected_intervention ?? data.final.decision).replaceAll("_", " ")}</p><p className="mt-1 text-xs text-slate-400">{data.final.decision} · {data.final.channel?.replaceAll("_", " ") ?? "No customer surface"}</p></div>
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3"><CheckCircle2 className="h-5 w-5 text-emerald-300" /><div><p className="text-[10px] uppercase text-emerald-400">Confidence</p><p className="font-mono text-xl font-semibold text-emerald-200">{(data.final.confidence * 100).toFixed(1)}%</p></div></div>
      </section>

      <div className="grid gap-5 xl:grid-cols-2"><RiskGauge probability={data.risk.probability} band={data.risk.band} /><CauseBarChart causes={data.root_causes} /></div>
      <div className="mt-5"><CandidateTable candidates={data.candidates} /></div>
      <div className="mt-5 grid gap-5 xl:grid-cols-2"><PolicyReasonList candidates={data.candidates} />{winner ? <UtilityBreakdownChart intervention={winner.intervention} score={winner.score} breakdown={winner.score_breakdown} runnerUp={runnerUp} /> : <section className="rounded-xl border border-slate-800 bg-slate-900 p-5 text-sm text-slate-500">No approved candidate required utility scoring.</section>}</div>
      <div className="mt-5 grid gap-5 xl:grid-cols-[1.2fr_.8fr]"><ExplanationTrail trace={data} /><LatencyBreakdown latency={data.latency_ms} /></div>
      <div className="mt-5 text-slate-900"><TraceWaterfall run={pipelineRun(data)} /></div>
    </div>
  );
}
