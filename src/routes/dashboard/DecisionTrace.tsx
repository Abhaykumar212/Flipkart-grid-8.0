import { useState } from "react";
import { ArrowLeft, CheckCircle2, Languages, RefreshCw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { AgentPipeline } from "../../components/dashboard/AgentPipeline";
import { CandidateTable } from "../../components/dashboard/CandidateTable";
import { CauseBarChart } from "../../components/dashboard/CauseBarChart";
import { ExplanationTrail } from "../../components/dashboard/ExplanationTrail";
import { LatencyBreakdown } from "../../components/dashboard/LatencyBreakdown";
import { PolicyReasonList } from "../../components/dashboard/PolicyReasonList";
import { RiskGauge } from "../../components/dashboard/RiskGauge";
import { UtilityBreakdownChart } from "../../components/dashboard/UtilityBreakdownChart";
import { titleCase } from "../../lib/metrics";
import { useDecisionTrace } from "../../hooks/useDecisionTrace";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिंदी" },
];

/** The four outputs the brief asks for, stated together and up front. */
function AnswerCard({ trace }: { trace: ReturnType<typeof useDecisionTrace>["data"] }) {
  if (!trace) return null;
  const dominant = [...trace.root_causes].sort((a, b) => b.probability - a.probability)[0];
  return (
    <section className="mb-5 grid gap-px overflow-hidden rounded-xl border border-cyan-500/25 bg-slate-800 sm:grid-cols-2 xl:grid-cols-4">
      {[
        {
          label: "Abandonment probability",
          value: `${Math.min(99, Math.max(1, Math.round(trace.risk.probability * 100)))}%`,
          detail: `${trace.risk.band} risk band`,
        },
        {
          label: "Root cause",
          value: dominant ? titleCase(dominant.cause) : "Not diagnosed",
          detail: dominant ? `${(dominant.probability * 100).toFixed(1)}% confidence` : "Below threshold",
        },
        {
          label: "Recommended intervention",
          value: titleCase(trace.final.selected_intervention ?? trace.final.decision),
          detail: trace.final.channel ? titleCase(trace.final.channel) : "No customer surface",
        },
        {
          label: "Confidence score",
          value: `${(trace.final.confidence * 100).toFixed(1)}%`,
          detail: trace.final.decision,
        },
      ].map((item) => (
        <div key={item.label} className="bg-slate-900 px-5 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-300">{item.label}</p>
          <p className="mt-2 text-lg font-semibold leading-tight text-white">{item.value}</p>
          <p className="mt-1 text-xs text-slate-500">{item.detail}</p>
        </div>
      ))}
    </section>
  );
}

export default function DecisionTrace() {
  const { decisionId = "" } = useParams();
  const [language, setLanguage] = useState("en");
  const { data, loading, error, refresh, stream } = useDecisionTrace(decisionId, language);

  if (loading && !data) return <div className="h-96 animate-pulse rounded-xl bg-slate-900" />;
  if (error || !data) {
    return (
      <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 text-rose-200">
        {error ?? "Decision not found"}
      </div>
    );
  }

  const winner =
    data.utility_scores.find((item) => item.intervention === data.final.selected_intervention)
    ?? data.utility_scores[0];
  const runnerUp = data.utility_scores.find((item) => item.intervention !== winner?.intervention);

  return (
    <div>
      <header className="mb-7">
        <Link
          to={`/dashboard/sessions/${data.session_id}`}
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-cyan-300"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Session {data.session_id}
        </Link>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-xs text-cyan-300">{data.decision_id}</p>
            <h1 className="mt-1 text-3xl font-semibold text-white">Full decision trace</h1>
            <p className="mt-2 text-sm text-slate-400">
              Triggered by {titleCase(data.trigger)} · {new Date(data.decision_time).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 p-1"
              role="group"
              aria-label="Explanation language"
            >
              <Languages className="ml-1.5 h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
              {LANGUAGES.map((item) => (
                <button
                  key={item.code}
                  type="button"
                  onClick={() => setLanguage(item.code)}
                  aria-pressed={language === item.code}
                  className={`rounded px-2.5 py-1 text-xs transition ${
                    language === item.code
                      ? "bg-cyan-500/15 font-semibold text-cyan-200"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => void refresh()}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:border-slate-600 hover:text-white"
            >
              <span
                className={`h-2 w-2 rounded-full ${stream.status === "connected" ? "bg-emerald-400" : "bg-amber-400"}`}
              />
              <RefreshCw className="h-3.5 w-3.5" />
              Live
            </button>
          </div>
        </div>
      </header>

      <AnswerCard trace={data} />

      <section className="mb-5 flex flex-wrap items-center justify-between gap-5 rounded-xl border border-cyan-500/25 bg-gradient-to-r from-cyan-500/10 to-slate-900 p-5">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">Final recommendation</p>
          <p className="mt-2 text-2xl font-semibold text-white">
            {titleCase(data.final.selected_intervention ?? data.final.decision)}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            {data.final.decision} · {data.final.channel ? titleCase(data.final.channel) : "No customer surface"}
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-300" />
          <div>
            <p className="text-[10px] uppercase text-emerald-400">Confidence</p>
            <p className="font-mono text-xl font-semibold text-emerald-200">
              {(data.final.confidence * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-2">
        <RiskGauge probability={data.risk.probability} band={data.risk.band} />
        <CauseBarChart causes={data.root_causes} />
      </div>
      <div className="mt-5">
        <CandidateTable candidates={data.candidates} />
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <PolicyReasonList candidates={data.candidates} />
        {winner ? (
          <UtilityBreakdownChart
            intervention={winner.intervention}
            score={winner.score}
            breakdown={winner.score_breakdown}
            runnerUp={runnerUp}
          />
        ) : (
          <section className="rounded-xl border border-slate-800 bg-slate-900 p-5 text-sm text-slate-500">
            No approved candidate required utility scoring.
          </section>
        )}
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-[1.2fr_.8fr]">
        <ExplanationTrail trace={data} language={language} />
        <LatencyBreakdown latency={data.latency_ms} />
      </div>
      <div className="mt-5">
        <AgentPipeline latency={data.latency_ms} />
      </div>
    </div>
  );
}
