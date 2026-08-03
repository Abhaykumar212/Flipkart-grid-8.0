import {
  ArrowDown,
  BrainCircuit,
  Database,
  Layers,
  MessageSquareText,
  Radio,
  Scale,
  ShieldCheck,
  ShoppingCart,
  Target,
} from "lucide-react";
import { PageHeader, Panel } from "../../components/dashboard/Panel";

/**
 * The architecture diagram, in the product rather than in a slide deck.
 *
 * The brief lists an architecture diagram as a required deliverable, and a
 * reviewer reading the dashboard should not have to open a separate document to
 * find out what produced the numbers in front of them.
 */

const AGENTS = [
  {
    icon: Layers,
    name: "Feature Agent",
    role: "Rebuilds the canonical 67-signal vector",
    detail:
      "Replays the immutable event log into session state, then computes one frozen feature contract shared by simulation, training, and serving. Intervention-history signals are excluded from risk training to prevent leakage.",
    outputs: "67 features · fs-v1",
  },
  {
    icon: BrainCircuit,
    name: "Risk Agent",
    role: "Calibrated abandonment probability",
    detail:
      "Gradient-boosted classifier with isotonic calibration, returning a probability, a risk band, and per-feature SHAP attribution. Model failure degrades to ABSTAIN rather than a guess.",
    outputs: "probability · band · SHAP",
  },
  {
    icon: Target,
    name: "Reasoning Agent",
    role: "Multi-label root-cause inference",
    detail:
      "Predicts which of ten supported causes the evidence backs, constrained to a frozen evidence family per cause. Conflicting signals produce UNKNOWN instead of a fabricated diagnosis.",
    outputs: "ranked causes · evidence keys",
  },
  {
    icon: ShieldCheck,
    name: "Policy Agent",
    role: "Eleven ordered safety rules",
    detail:
      "Screens every candidate in the closed 12-intervention catalogue before any ranking happens. Fatigue, margin, eligibility, and discount protection can all override model confidence, and each rejection carries a closed reason code.",
    outputs: "pass / reject / downgrade",
  },
  {
    icon: Scale,
    name: "Recommendation Agent",
    role: "Utility ranking over approved actions",
    detail:
      "Scores only what policy already approved, trading expected uplift and relevance against direct cost, margin risk, fatigue, and intrusiveness. An optional contextual bandit may reorder approved actions but can never introduce a rejected one.",
    outputs: "ranked utility · confidence",
  },
  {
    icon: MessageSquareText,
    name: "Explainability Agent",
    role: "Grounded justification trail",
    detail:
      "Builds evidence → prediction → inference → policy → action statements from the persisted trace. Optional LLM rendering is checked against the structured facts and discarded if it drifts; the deterministic template is always the fallback.",
    outputs: "trail · prose (en / hi)",
  },
];

const GUARANTEES = [
  {
    title: "Silence is a decision",
    detail:
      "NO_ACTION and ABSTAIN are persisted with the same audit bundle as an intervention, so restraint is measurable rather than invisible.",
  },
  {
    title: "Policy runs before ranking",
    detail:
      "A high-confidence model cannot route around a safety rule, because rejected candidates never reach the ranker.",
  },
  {
    title: "Discounts need five independent checks",
    detail:
      "Verified price sensitivity, margin headroom, eligibility, budget, and fatigue must all pass. The counterfactual is recorded even when no discount was considered.",
  },
  {
    title: "Every decision is replayable",
    detail:
      "Session state is rebuildable from the event log, and the exact serving feature vector is persisted alongside the decision that used it.",
  },
  {
    title: "Failure is safe by construction",
    detail:
      "A missing model, a dead LLM, or an unreachable review cache degrades to a quieter decision, never to an unexplained one.",
  },
  {
    title: "Offline by default",
    detail:
      "SQLite, local model artifacts, and deterministic templates mean the demo does not depend on venue Wi-Fi or an API key.",
  },
];

function AgentNode({ agent, index }: { agent: (typeof AGENTS)[number]; index: number }) {
  const Icon = agent.icon;
  return (
    <li>
      <div className="flex gap-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-cyan-500/15 text-cyan-300">
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-white">{agent.name}</h3>
            <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
              stage {index + 1}
            </span>
          </div>
          <p className="mt-0.5 text-xs font-medium text-cyan-300/80">{agent.role}</p>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">{agent.detail}</p>
          <p className="mt-2 font-mono text-[10px] text-slate-600">→ {agent.outputs}</p>
        </div>
      </div>
      {index < AGENTS.length - 1 && <ArrowDown className="mx-auto my-1.5 h-4 w-4 text-slate-700" />}
    </li>
  );
}

export default function Architecture() {
  return (
    <div>
      <PageHeader
        eyebrow="System design"
        title="Architecture"
        description="How a browser event becomes a governed, explainable intervention — and what stops it becoming a blanket coupon."
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-5">
          <Panel
            title="Ingress"
            subtitle="Everything downstream is derived from an append-only event log."
          >
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                {
                  icon: ShoppingCart,
                  name: "Storefront",
                  detail: "21 strictly validated event types emitted from the React shopfront",
                },
                {
                  icon: Database,
                  name: "Event ingestion",
                  detail: "Idempotent, ordered, immutable persistence with late-event marking",
                },
                {
                  icon: Radio,
                  name: "Trigger gate",
                  detail: "Debounce, minimum interval, and material-change checks before any spend",
                },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.name} className="rounded-lg border border-slate-800 bg-slate-950/50 p-4">
                    <Icon className="h-4 w-4 text-cyan-300" />
                    <p className="mt-2 text-xs font-semibold text-white">{item.name}</p>
                    <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{item.detail}</p>
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel
            title="Agent orchestration"
            subtitle="Six specialised agents in a fixed order. No single heuristic decides anything."
          >
            <ol>
              {AGENTS.map((agent, index) => (
                <AgentNode key={agent.name} agent={agent} index={index} />
              ))}
            </ol>
          </Panel>

          <Panel
            title="Feedback loop"
            subtitle="What happened next is written back against the decision that caused it."
          >
            <div className="grid gap-3 sm:grid-cols-4">
              {[
                { name: "Impression", detail: "Surface and channel recorded when shown" },
                { name: "Engagement", detail: "Click or dismissal attributed to the decision" },
                { name: "Conversion", detail: "Order value, discount cost, estimated margin" },
                { name: "Learning", detail: "Affinity priors and optional bandit posteriors" },
              ].map((item) => (
                <div key={item.name} className="rounded-lg border border-slate-800 bg-slate-950/50 p-4">
                  <p className="text-xs font-semibold text-white">{item.name}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{item.detail}</p>
                </div>
              ))}
            </div>
          </Panel>
        </div>

        <div className="min-w-0 space-y-5">
          <Panel title="Design guarantees" subtitle="The claims this system is prepared to defend.">
            <ul className="space-y-4">
              {GUARANTEES.map((item) => (
                <li key={item.title}>
                  <p className="text-xs font-semibold text-white">{item.title}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{item.detail}</p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Stack" subtitle="Deliberately boring where it does not need to be clever.">
            <dl className="space-y-2.5 text-xs">
              {[
                ["Storefront", "React 19 · Vite · Tailwind"],
                ["Service", "FastAPI · SQLAlchemy modular monolith"],
                ["Store", "SQLite by default · PostgreSQL by config"],
                ["Models", "XGBoost + isotonic calibration · SHAP"],
                ["Retrieval", "TF-IDF over sanitised review corpus"],
                ["LLM", "Optional Groq · never in the decision path"],
                ["Streaming", "Server-sent events to the dashboard"],
              ].map(([name, value]) => (
                <div key={name} className="flex items-baseline justify-between gap-3">
                  <dt className="shrink-0 text-slate-500">{name}</dt>
                  <dd className="text-right text-slate-300">{value}</dd>
                </div>
              ))}
            </dl>
          </Panel>
        </div>
      </div>
    </div>
  );
}
