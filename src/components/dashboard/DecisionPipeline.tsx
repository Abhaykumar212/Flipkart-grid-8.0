import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  BadgeCheck,
  BrainCircuit,
  ChevronRight,
  CircleSlash2,
  DatabaseZap,
  FileSearch,
  Filter,
  Gauge,
  ListChecks,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { featureLabel } from "../../lib/featureLabels";
import { formatMs, formatProbability, formatRupees, titleCase } from "../../lib/metrics";
import type {
  DashboardCandidate,
  DecisionTraceResponse,
  SessionDetailResponse,
} from "../../types/dashboard";

type StageTone = "data" | "risk" | "reason" | "policy" | "success" | "neutral";

interface StageValue {
  label: string;
  value: string;
}

interface StageGroup {
  title: string;
  rows: StageValue[];
}

interface PipelineStage {
  id: string;
  name: string;
  shortName: string;
  status: string;
  headline: string;
  tone: StageTone;
  icon: typeof Activity;
  latency?: number;
  version?: string;
  inputs: StageValue[];
  process: string;
  outputs: StageValue[];
  groups?: StageGroup[];
  safeguard?: string;
}

const TONE = {
  data: {
    border: "border-teal-400/45",
    bg: "bg-teal-400/10",
    icon: "bg-teal-400/15 text-teal-200",
    text: "text-teal-200",
    dot: "bg-teal-300",
    line: "bg-teal-400",
  },
  risk: {
    border: "border-rose-400/45",
    bg: "bg-rose-400/10",
    icon: "bg-rose-400/15 text-rose-200",
    text: "text-rose-200",
    dot: "bg-rose-300",
    line: "bg-rose-400",
  },
  reason: {
    border: "border-blue-400/50",
    bg: "bg-blue-400/10",
    icon: "bg-blue-400/15 text-blue-200",
    text: "text-blue-200",
    dot: "bg-blue-300",
    line: "bg-blue-400",
  },
  policy: {
    border: "border-amber-400/50",
    bg: "bg-amber-400/10",
    icon: "bg-amber-400/15 text-amber-200",
    text: "text-amber-200",
    dot: "bg-amber-300",
    line: "bg-amber-400",
  },
  success: {
    border: "border-emerald-400/50",
    bg: "bg-emerald-400/10",
    icon: "bg-emerald-400/15 text-emerald-200",
    text: "text-emerald-200",
    dot: "bg-emerald-300",
    line: "bg-emerald-400",
  },
  neutral: {
    border: "border-zinc-500/55",
    bg: "bg-zinc-500/10",
    icon: "bg-zinc-500/15 text-zinc-200",
    text: "text-zinc-200",
    dot: "bg-zinc-300",
    line: "bg-zinc-400",
  },
} satisfies Record<StageTone, Record<string, string>>;

function valueText(value: number): string {
  if (Number.isInteger(value)) return value.toLocaleString("en-IN");
  if (Math.abs(value) >= 1000) return value.toLocaleString("en-IN", { maximumFractionDigits: 1 });
  return value.toFixed(3);
}

function exactPercent(value: number, digits = 0): string {
  return `${(Math.max(0, Math.min(1, value)) * 100).toFixed(digits)}%`;
}

function candidateResult(candidate: DashboardCandidate): string {
  const reason = candidate.policy_reasons.map(titleCase).join(", ");
  if (candidate.policy_status === "REJECT") return reason || "Rejected by policy";
  if (candidate.selected) return `Selected / utility ${(candidate.utility_score ?? 0).toFixed(3)}`;
  return candidate.utility_score === null ? candidate.policy_status : `Utility ${candidate.utility_score.toFixed(3)}`;
}

function outcomeLabel(trace: DecisionTraceResponse): string {
  const outcome = trace.outcome;
  if (outcome?.order_completed) return "Converted";
  if (outcome?.dismissed) return "Dismissed";
  if (outcome?.clicked) return "Engaged";
  if (outcome?.intervention_shown) return "Shown";
  if (trace.final.decision === "INTERVENE") return "Awaiting response";
  return "Deliberately silent";
}

function buildStages(
  trace: DecisionTraceResponse,
  session: SessionDetailResponse,
): PipelineStage[] {
  const dominant = [...trace.root_causes].sort((left, right) => right.probability - left.probability)[0];
  const approved = trace.candidates.filter((candidate) => candidate.policy_status === "PASS");
  const rejected = trace.candidates.filter((candidate) => candidate.policy_status === "REJECT");
  const featureRows = Object.entries(trace.feature_snapshot?.features ?? {}).map(([name, value]) => ({
    label: featureLabel(name),
    value: valueText(value),
  }));
  const eventRows = session.timeline.map((event) => ({
    label: `#${event.sequence_no} ${titleCase(event.event_type)}`,
    value: new Date(event.server_timestamp).toLocaleTimeString(),
  }));
  const utilityRows = trace.utility_scores.map((score) => ({
    label: titleCase(score.intervention),
    value: `${score.score.toFixed(3)} / ${(score.confidence * 100).toFixed(0)}% confidence`,
  }));
  const observationRows = trace.explanation.observations.map((observation) => ({
    label: featureLabel(observation.feature),
    value: observation.statement,
  }));
  const versionRows = Object.entries(trace.model_versions).map(([name, version]) => ({
    label: titleCase(name),
    value: version,
  }));
  const policyRows = trace.candidates.map((candidate) => ({
    label: titleCase(candidate.intervention),
    value: candidateResult(candidate),
  }));
  const winningUtility = trace.utility_scores.find(
    (score) => score.intervention === trace.final.selected_intervention,
  );
  const riskTone: StageTone = trace.risk.band === "LOW" ? "success" : "risk";
  const finalTone: StageTone = trace.final.decision === "INTERVENE" ? "success" : "neutral";
  const unknownCause = dominant?.cause === "UNKNOWN";
  const intervened = trace.final.decision === "INTERVENE";

  return [
    {
      id: "events",
      name: "Session Events",
      shortName: "Events",
      status: "VALIDATED",
      headline: `${session.timeline.length} ordered events`,
      tone: "data",
      icon: DatabaseZap,
      inputs: [
        { label: "Device", value: session.session.device_type ?? "Unknown" },
        { label: "Entry", value: titleCase(session.session.referral_source ?? "Direct") },
        { label: "Current route", value: session.session.current_route ?? "Not reported" },
      ],
      process: "Validate the event contract, preserve server order, and rebuild the current cart session.",
      outputs: [
        { label: "Accepted events", value: session.timeline.length.toLocaleString("en-IN") },
        { label: "Decision trigger", value: titleCase(trace.trigger) },
        { label: "Cart context", value: `${session.cart.item_count} item / ${formatRupees(session.cart.value)}` },
      ],
      groups: [{ title: "Immutable event stream", rows: eventRows }],
      safeguard: "Duplicate events are idempotent and late arrivals are marked rather than silently reordered.",
    },
    {
      id: "features",
      name: "Feature Agent",
      shortName: "Features",
      status: "READY",
      headline: `${featureRows.length} serving signals`,
      tone: "data",
      icon: Filter,
      latency: trace.latency_ms.features,
      version: trace.feature_snapshot?.feature_schema_version,
      inputs: [
        { label: "Event state", value: `${session.timeline.length} events` },
        { label: "Cart", value: `${session.cart.item_count} item / ${formatRupees(session.cart.value)}` },
        { label: "Context", value: session.session.device_type ?? "Unknown device" },
      ],
      process: "Apply the frozen online feature contract shared by simulation, training, and serving.",
      outputs: [
        { label: "Feature vector", value: `${featureRows.length} values` },
        { label: "Schema", value: trace.feature_snapshot?.feature_schema_version ?? "Unavailable" },
        { label: "Evidence signals", value: `${trace.explanation.observations.length} highlighted` },
      ],
      groups: [
        { title: "Evidence used by this decision", rows: observationRows },
        { title: "Complete feature snapshot", rows: featureRows },
      ],
      safeguard: "The persisted vector is the exact vector used for serving and can be replayed from the event log.",
    },
    {
      id: "risk",
      name: "Risk Agent",
      shortName: "Risk",
      status: trace.risk.band,
      headline: `${formatProbability(trace.risk.probability)} abandonment`,
      tone: riskTone,
      icon: Gauge,
      latency: trace.latency_ms.risk,
      version: trace.risk.model_version,
      inputs: trace.explanation.observations.slice(0, 3).map((observation) => ({
        label: featureLabel(observation.feature),
        value: valueText(observation.value),
      })),
      process: "Run calibrated gradient-boosted inference and retain feature-level attribution.",
      outputs: [
        { label: "Probability", value: formatProbability(trace.risk.probability) },
        { label: "Risk band", value: trace.risk.band },
        { label: "Interpretation", value: trace.risk.statement },
      ],
      groups: [{ title: "Risk evidence", rows: observationRows }],
      safeguard: "Model loading or inference failure fails safely instead of returning an ungrounded score.",
    },
    {
      id: "root-cause",
      name: "Root-Cause Agent",
      shortName: "Root Cause",
      status: unknownCause ? "UNCERTAIN" : "DIAGNOSED",
      headline: dominant ? titleCase(dominant.cause) : "No supported cause",
      tone: unknownCause ? "neutral" : "reason",
      icon: BrainCircuit,
      latency: trace.latency_ms.root_cause,
      version: trace.model_versions.root_cause,
      inputs: (dominant?.evidence_keys ?? []).map((key) => ({
        label: featureLabel(key),
        value: trace.feature_snapshot?.features[key] === undefined
          ? "Evidence present"
          : valueText(trace.feature_snapshot.features[key]),
      })),
      process: "Compare supported evidence families across the controlled multi-label cause taxonomy.",
      outputs: [
        { label: "Dominant cause", value: dominant ? titleCase(dominant.cause) : "Not diagnosed" },
        { label: unknownCause ? "Evidence state" : "Cause confidence", value: unknownCause ? "Conflicting signals" : dominant ? exactPercent(dominant.probability) : "Unavailable" },
        { label: "Uncertainty", value: trace.explanation.uncertainty.statement },
      ],
      groups: [{
        title: "Ranked supported causes",
        rows: trace.root_causes.map((cause) => ({
          label: titleCase(cause.cause),
          value: cause.cause === "UNKNOWN" ? "Conflicting evidence" : `${exactPercent(cause.probability)} / ${cause.evidence_keys.length} evidence signals`,
        })),
      }],
      safeguard: "Conflicting or weak evidence resolves to UNKNOWN rather than inventing shopper intent.",
    },
    {
      id: "policy",
      name: "Policy Agent",
      shortName: "Policy",
      status: rejected.length > 0 ? "GUARDED" : "CLEARED",
      headline: `${approved.length} pass / ${rejected.length} rejected`,
      tone: "policy",
      icon: ShieldCheck,
      latency: trace.latency_ms.policy_and_rank,
      version: trace.model_versions.policy,
      inputs: [
        { label: "Generated candidates", value: trace.candidates.filter((candidate) => candidate.generated).length.toString() },
        { label: "Prior dismissals", value: valueText(trace.feature_snapshot?.features.i_dismissal_count ?? 0) },
        { label: "Discount evidence", value: rejected.some((candidate) => candidate.intervention.includes("DISCOUNT")) ? "Checked" : "Not required" },
      ],
      process: "Apply ordered eligibility, fatigue, margin, and discount-protection rules before ranking.",
      outputs: [
        { label: "Approved", value: approved.map((candidate) => titleCase(candidate.intervention)).join(", ") || "None" },
        { label: "Rejected", value: rejected.map((candidate) => titleCase(candidate.intervention)).join(", ") || "None" },
        { label: "Discount decision", value: trace.audit_answers.discount_not_offered },
      ],
      groups: [{ title: "Candidate policy results", rows: policyRows }],
      safeguard: "Rejected actions never reach the utility ranker, regardless of model confidence.",
    },
    {
      id: "recommendation",
      name: "Recommendation Agent",
      shortName: "Recommend",
      status: intervened ? "SELECTED" : "RESTRAINED",
      headline: titleCase(trace.final.selected_intervention ?? trace.final.decision),
      tone: intervened ? "data" : "neutral",
      icon: ListChecks,
      latency: trace.latency_ms.policy_and_rank,
      version: trace.model_versions.ranker,
      inputs: [
        { label: "Policy-approved", value: approved.length.toString() },
        { label: "Dominant cause", value: dominant ? titleCase(dominant.cause) : "None" },
        { label: "Decision confidence", value: exactPercent(trace.final.confidence) },
      ],
      process: "Rank only approved actions by relevance and expected uplift minus cost, fatigue, margin risk, and intrusiveness.",
      outputs: [
        { label: "Winner", value: titleCase(trace.final.selected_intervention ?? trace.final.decision) },
        { label: "Utility", value: winningUtility?.score.toFixed(3) ?? "No action required" },
        { label: "Surface", value: titleCase(trace.final.channel ?? "No customer surface") },
      ],
      groups: [
        { title: "Utility ranking", rows: utilityRows },
        ...(winningUtility ? [{
          title: "Winning utility breakdown",
          rows: Object.entries(winningUtility.score_breakdown).map(([name, value]) => ({
            label: titleCase(name),
            value: value.toFixed(3),
          })),
        }] : []),
      ],
      safeguard: "Lower-cost actions win close scores and NO_ACTION remains an explicit candidate.",
    },
    {
      id: "explain",
      name: "Explainability Agent",
      shortName: "Explain",
      status: "GROUNDED",
      headline: `${trace.explanation.observations.length} evidence statements`,
      tone: "reason",
      icon: MessageSquareText,
      latency: trace.latency_ms.explain,
      version: trace.explanation.rendered_by,
      inputs: [
        { label: "Observations", value: trace.explanation.observations.length.toString() },
        { label: "Rejected actions", value: trace.explanation.rejected.length.toString() },
        { label: "Structured versions", value: Object.keys(trace.explanation.versions).length.toString() },
      ],
      process: "Assemble evidence, prediction, inference, policy, and action into an auditable human explanation.",
      outputs: [
        { label: "Risk", value: trace.audit_answers.elevated_risk },
        { label: "Cause", value: trace.audit_answers.root_cause },
        { label: "Action", value: trace.audit_answers.selected_intervention },
      ],
      groups: [
        { title: "Observed evidence", rows: observationRows },
        { title: "Version provenance", rows: versionRows },
      ],
      safeguard: "Optional LLM prose is discarded if it drifts from the persisted structured facts.",
    },
    {
      id: "action",
      name: "Customer Action",
      shortName: "Action",
      status: trace.final.decision,
      headline: titleCase(trace.final.selected_intervention ?? trace.final.decision),
      tone: finalTone,
      icon: trace.final.decision === "INTERVENE" ? Sparkles : CircleSlash2,
      latency: trace.latency_ms.total,
      version: trace.final.channel ?? undefined,
      inputs: [
        { label: "Authorized decision", value: trace.final.decision },
        { label: "Intervention", value: titleCase(trace.final.selected_intervention ?? "None") },
        { label: "Channel", value: titleCase(trace.final.channel ?? "No surface") },
      ],
      process: "Render only the backend-authorized surface, or preserve silence when policy abstains.",
      outputs: [
        { label: "Customer state", value: outcomeLabel(trace) },
        { label: "Order", value: trace.outcome?.order_completed ? "Completed" : "Not completed" },
        { label: "Discount cost", value: formatRupees(trace.outcome?.discount_cost ?? 0) },
      ],
      groups: trace.outcome ? [{
        title: "Recorded response",
        rows: [
          { label: "Shown", value: trace.outcome.intervention_shown ? "Yes" : "No" },
          { label: "Clicked", value: trace.outcome.clicked ? "Yes" : "No" },
          { label: "Dismissed", value: trace.outcome.dismissed ? "Yes" : "No" },
          { label: "Converted", value: trace.outcome.order_completed ? "Yes" : "No" },
        ],
      }] : undefined,
      safeguard: "Unverified content, unsupported promises, and unauthorized discounts never reach the customer surface.",
    },
  ];
}

function ValueList({ rows }: { rows: StageValue[] }) {
  return (
    <dl className="divide-y divide-white/5">
      {rows.map((row, index) => (
        <div key={`${row.label}-${index}`} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)] gap-3 py-2.5 text-xs">
          <dt className="text-zinc-500">{row.label}</dt>
          <dd className="break-words text-right leading-relaxed text-zinc-200">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function StageInspector({ stage, index }: { stage: PipelineStage; index: number }) {
  const Icon = stage.icon;
  const tone = TONE[stage.tone];
  return (
    <aside aria-live="polite" className="min-h-0 border-t border-zinc-800 bg-[#0d1117] 2xl:border-l 2xl:border-t-0">
      <div className="flex items-start justify-between gap-3 border-b border-zinc-800 px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-md ${tone.icon}`}>
            <Icon className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-500">Stage {index + 1}</p>
            <h3 className="mt-0.5 truncate text-sm font-semibold text-white">{stage.name}</h3>
          </div>
        </div>
        <span className={`rounded border px-2 py-1 text-[10px] font-semibold ${tone.border} ${tone.bg} ${tone.text}`}>
          {stage.status}
        </span>
      </div>

      <div className="max-h-[calc(100vh-238px)] overflow-y-auto px-5 py-4">
        <section>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-300">Input</p>
          <ValueList rows={stage.inputs} />
        </section>

        <section className="my-4 border-y border-zinc-800 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-500">Transformation</p>
          <p className="mt-2 text-xs leading-relaxed text-zinc-300">{stage.process}</p>
        </section>

        <section>
          <p className={`text-[10px] font-semibold uppercase tracking-[0.16em] ${tone.text}`}>Output</p>
          <ValueList rows={stage.outputs} />
        </section>

        {stage.groups?.map((group) => (
          <section key={group.title} className="mt-5 border-t border-zinc-800 pt-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-500">{group.title}</p>
            <ValueList rows={group.rows} />
          </section>
        ))}

        {stage.safeguard && (
          <section className="mt-5 border border-amber-400/20 bg-amber-400/5 p-3">
            <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-amber-300">
              <ShieldCheck className="h-3.5 w-3.5" />
              Safeguard
            </p>
            <p className="mt-2 text-xs leading-relaxed text-amber-100/75">{stage.safeguard}</p>
          </section>
        )}
      </div>

      {(stage.latency !== undefined || stage.version) && (
        <footer className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-zinc-800 px-5 py-3 font-mono text-[10px] text-zinc-500">
          {stage.latency !== undefined && <span>{formatMs(stage.latency)}</span>}
          {stage.version && <span>{stage.version}</span>}
        </footer>
      )}
    </aside>
  );
}

function AnswerBand({ trace }: { trace: DecisionTraceResponse }) {
  const dominant = [...trace.root_causes].sort((left, right) => right.probability - left.probability)[0];
  const answers = [
    {
      label: "Abandonment risk",
      value: formatProbability(trace.risk.probability),
      detail: `${titleCase(trace.risk.band)} risk`,
      tone: "text-rose-200",
    },
    {
      label: "Root cause",
      value: titleCase(dominant?.cause ?? "Not diagnosed"),
      detail: dominant?.cause === "UNKNOWN" ? "Conflicting signals" : dominant ? `${exactPercent(dominant.probability)} supported` : "No supported evidence",
      tone: "text-blue-200",
    },
    {
      label: "Recommended action",
      value: titleCase(trace.final.selected_intervention ?? trace.final.decision),
      detail: titleCase(trace.final.channel ?? "No customer surface"),
      tone: trace.final.decision === "INTERVENE" ? "text-teal-200" : "text-zinc-200",
    },
    {
      label: "Decision confidence",
      value: exactPercent(trace.final.confidence),
      detail: trace.final.decision,
      tone: "text-emerald-200",
    },
  ];

  return (
    <section aria-label="Required decision outputs" className="grid border-b border-zinc-800 bg-[#0d1117] sm:grid-cols-2 xl:grid-cols-4">
      {answers.map((answer) => (
        <div key={answer.label} className="min-w-0 border-b border-r border-zinc-800 px-4 py-3 last:border-r-0 sm:[&:nth-child(n+3)]:border-b-0 xl:border-b-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">{answer.label}</p>
          <p className={`mt-1.5 truncate text-base font-semibold ${answer.tone}`} title={answer.value}>{answer.value}</p>
          <p className="mt-0.5 text-[11px] text-zinc-500">{answer.detail}</p>
        </div>
      ))}
    </section>
  );
}

export function DecisionPipeline({
  trace,
  session,
}: {
  trace: DecisionTraceResponse;
  session: SessionDetailResponse;
}) {
  const stages = useMemo(() => buildStages(trace, session), [trace, session]);
  const [revealed, setRevealed] = useState(0);
  const [selectedId, setSelectedId] = useState(stages[0].id);
  const interrupted = useRef(false);

  useEffect(() => {
    interrupted.current = false;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setRevealed(stages.length);
      setSelectedId(stages.at(-1)?.id ?? stages[0].id);
      return;
    }

    setRevealed(0);
    setSelectedId(stages[0].id);
    const timers = stages.map((stage, index) => window.setTimeout(() => {
      if (interrupted.current) return;
      setRevealed(index + 1);
      setSelectedId(stage.id);
    }, 220 + index * 430));
    return () => timers.forEach(window.clearTimeout);
  }, [trace.decision_id, stages]);

  const selectStage = (stage: PipelineStage) => {
    interrupted.current = true;
    setRevealed(stages.length);
    setSelectedId(stage.id);
  };

  const selectedIndex = Math.max(0, stages.findIndex((stage) => stage.id === selectedId));
  const selectedStage = stages[selectedIndex];
  const behavior = trace.explanation.observations.slice(0, 4);

  return (
    <section className="overflow-hidden border border-zinc-800 bg-[#090d13] shadow-2xl shadow-black/20">
      <AnswerBand trace={trace} />

      <div className="grid min-h-[590px] 2xl:grid-cols-[minmax(0,1fr)_330px]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-zinc-800 bg-black/15 px-5 py-3">
            <span className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">
              <Activity className="h-3.5 w-3.5 text-teal-300" />
              Observed behavior
            </span>
            {behavior.map((observation) => (
              <span key={observation.feature} className="text-xs text-zinc-300">{observation.statement}</span>
            ))}
          </div>

          <div className="relative px-4 py-7 sm:px-5">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.17em] text-blue-300">Live architecture trace</p>
                <h2 className="mt-1 text-lg font-semibold text-white">Evidence to customer action</h2>
              </div>
              <div className="hidden items-center gap-2 text-[10px] uppercase tracking-[0.12em] text-zinc-500 sm:flex">
                <span className="h-2 w-2 rounded-full bg-teal-300" />
                {revealed < stages.length ? `Resolving stage ${revealed + 1}` : "Trace complete"}
              </div>
            </div>

            <ol className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8" aria-label="Decision pipeline">
              {stages.map((stage, index) => {
                const Icon = stage.icon;
                const visible = index < revealed;
                const selected = stage.id === selectedId;
                const tone = TONE[stage.tone];
                return (
                  <li key={stage.id} className="group relative min-w-0">
                    <button
                      type="button"
                      onClick={() => selectStage(stage)}
                      aria-pressed={selected}
                      aria-label={`${stage.name}: ${stage.headline}`}
                      className={`relative flex h-[142px] w-full cursor-pointer flex-col items-start border p-3 text-left transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
                        visible ? `${tone.border} ${tone.bg}` : "border-zinc-800 bg-zinc-900/35 opacity-35"
                      } ${selected ? "ring-2 ring-blue-400 ring-offset-2 ring-offset-[#090d13]" : "hover:border-zinc-500"}`}
                    >
                      <span className="flex w-full items-start justify-between gap-2">
                        <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-md ${visible ? tone.icon : "bg-zinc-800 text-zinc-500"}`}>
                          <Icon className="h-4 w-4" />
                        </span>
                        <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${visible ? tone.dot : "bg-zinc-700"}`} />
                      </span>
                      <span className="mt-3 block text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-500">{index + 1}. {stage.shortName}</span>
                      <span className="mt-1 line-clamp-2 text-xs font-semibold leading-snug text-zinc-100">{visible ? stage.headline : "Awaiting input"}</span>
                      <span className={`mt-auto font-mono text-[9px] ${visible ? tone.text : "text-zinc-600"}`}>
                        {visible ? stage.status : "PENDING"}
                      </span>
                    </button>

                    {index < stages.length - 1 && (
                      <span aria-hidden="true" className="pointer-events-none absolute left-[calc(100%+1px)] top-[67px] z-10 hidden w-3 items-center xl:flex">
                        <span className={`h-px flex-1 transition-colors duration-300 ${index + 1 < revealed ? tone.line : "bg-zinc-800"}`} />
                        <ChevronRight className={`-ml-1 h-3 w-3 ${index + 1 < revealed ? tone.text : "text-zinc-700"}`} />
                      </span>
                    )}

                    <div className={`pointer-events-none absolute left-1/2 top-[calc(100%+8px)] z-30 hidden w-52 -translate-x-1/2 border border-zinc-700 bg-zinc-950 p-3 shadow-2xl ${selected ? "" : "group-hover:block"}`}>
                      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-teal-300">Input</p>
                      <p className="mt-1 truncate text-xs text-zinc-300">{stage.inputs[0]?.label}: {stage.inputs[0]?.value}</p>
                      <p className={`mt-2 text-[10px] font-semibold uppercase tracking-[0.12em] ${tone.text}`}>Output</p>
                      <p className="mt-1 line-clamp-2 text-xs text-zinc-200">{stage.outputs[0]?.label}: {stage.outputs[0]?.value}</p>
                    </div>
                  </li>
                );
              })}
            </ol>

            <div className="mt-7 grid gap-3 border-t border-zinc-800 pt-5 lg:grid-cols-[minmax(0,1fr)_260px]">
              <div className="flex min-w-0 gap-3">
                <FileSearch className="mt-0.5 h-4 w-4 shrink-0 text-blue-300" />
                <div className="min-w-0">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Decision path</p>
                  <p className="mt-1 text-xs leading-relaxed text-zinc-300">
                    {trace.audit_answers.elevated_risk} {trace.audit_answers.root_cause} {trace.audit_answers.selected_intervention}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 border-zinc-800 lg:border-l lg:pl-4">
                {trace.final.decision === "INTERVENE" ? (
                  <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
                ) : (
                  <CircleSlash2 className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400" />
                )}
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Customer result</p>
                  <p className="mt-1 text-xs font-semibold text-zinc-200">{outcomeLabel(trace)}</p>
                  <p className="mt-1 text-[11px] text-zinc-500">{titleCase(trace.final.selected_intervention ?? trace.final.decision)}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <StageInspector stage={selectedStage} index={selectedIndex} />
      </div>
    </section>
  );
}
