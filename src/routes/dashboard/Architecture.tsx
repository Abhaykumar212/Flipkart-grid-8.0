import {
  Activity,
  ArrowDown,
  ArrowRight,
  BrainCircuit,
  Database,
  FileCheck2,
  Filter,
  Gauge,
  GitBranch,
  History,
  Layers3,
  MessageSquareText,
  Radio,
  Scale,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "../../components/dashboard/Panel";

const AGENTS = [
  { icon: Filter, name: "Feature", output: "67 signals", tone: "text-teal-200 bg-teal-400/10 border-teal-400/30" },
  { icon: Gauge, name: "Risk", output: "Probability", tone: "text-rose-200 bg-rose-400/10 border-rose-400/30" },
  { icon: BrainCircuit, name: "Root cause", output: "Supported intent", tone: "text-blue-200 bg-blue-400/10 border-blue-400/30" },
  { icon: ShieldCheck, name: "Policy", output: "Pass / reject", tone: "text-amber-200 bg-amber-400/10 border-amber-400/30" },
  { icon: Scale, name: "Recommend", output: "Utility winner", tone: "text-teal-200 bg-teal-400/10 border-teal-400/30" },
  { icon: MessageSquareText, name: "Explain", output: "Grounded trail", tone: "text-blue-200 bg-blue-400/10 border-blue-400/30" },
];

const GUARANTEES = [
  { icon: ShieldCheck, title: "Policy before ranking", detail: "Rejected actions never reach utility scoring." },
  { icon: History, title: "Replayable decisions", detail: "Event log, feature vector, and versions are persisted." },
  { icon: FileCheck2, title: "Grounded explanations", detail: "Every statement maps back to structured evidence." },
  { icon: Activity, title: "Safe degradation", detail: "Failures become ABSTAIN or NO_ACTION, never guesses." },
  { icon: GitBranch, title: "Measured feedback", detail: "Impressions, response, conversion, and cost are attributed." },
];

function FlowArrow({ vertical = false }: { vertical?: boolean }) {
  return vertical
    ? <ArrowDown className="h-5 w-5 text-zinc-700" aria-hidden="true" />
    : <ArrowRight className="h-5 w-5 text-zinc-700" aria-hidden="true" />;
}

function BoundaryNode({
  icon: Icon,
  label,
  value,
  tone = "blue",
}: {
  icon: typeof ShoppingCart;
  label: string;
  value: string;
  tone?: "blue" | "teal" | "green";
}) {
  const color = tone === "teal"
    ? "border-teal-400/35 bg-teal-400/8 text-teal-200"
    : tone === "green"
      ? "border-emerald-400/35 bg-emerald-400/8 text-emerald-200"
      : "border-blue-400/35 bg-blue-400/8 text-blue-200";
  return (
    <div className={`flex min-h-24 items-center gap-3 border p-4 ${color}`}>
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-black/20">
        <Icon className="h-5 w-5" />
      </span>
      <div className="min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] opacity-70">{label}</p>
        <p className="mt-1 text-sm font-semibold text-white">{value}</p>
      </div>
    </div>
  );
}

export default function Architecture() {
  return (
    <div>
      <PageHeader
        eyebrow="System blueprint"
        title="One governed path from hesitation to help"
        description="The system stays event-driven and auditable: models propose, deterministic policy governs, and only an authorized action reaches the shopper."
      />

      <section aria-labelledby="online-flow" className="border border-zinc-800 bg-[#0d1117]">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 px-5 py-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-300">Online decision path</p>
            <h2 id="online-flow" className="mt-1 text-sm font-semibold text-white">Real-time architecture</h2>
          </div>
          <div className="flex items-center gap-4 font-mono text-[10px] text-zinc-500">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-teal-300" /> dashboard &lt; 1s</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-blue-300" /> decision &lt; 300ms</span>
          </div>
        </header>

        <div className="p-5">
          <div className="flex flex-col items-stretch gap-3 xl:flex-row xl:items-center">
            <div className="xl:w-[180px] xl:shrink-0">
              <BoundaryNode icon={ShoppingCart} label="Experience" value="Storefront events" />
            </div>
            <div className="hidden justify-center xl:flex"><FlowArrow /></div>
            <div className="xl:w-[190px] xl:shrink-0">
              <BoundaryNode icon={Radio} label="Ingress" value="Validate and trigger" tone="teal" />
            </div>
            <div className="hidden justify-center xl:flex"><FlowArrow /></div>

            <div className="min-w-0 border border-zinc-700 bg-[#090d13] p-4 xl:flex-1">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Layers3 className="h-4 w-4 text-blue-300" />
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-blue-300">Decision orchestrator</p>
                    <p className="mt-0.5 text-xs text-zinc-500">Fixed order, persisted trace</p>
                  </div>
                </div>
                <span className="border border-zinc-700 px-2 py-1 font-mono text-[9px] text-zinc-500">modular monolith</span>
              </div>
              <ol className="grid gap-2 sm:grid-cols-3 xl:grid-cols-6">
                {AGENTS.map((agent, index) => {
                  const Icon = agent.icon;
                  return (
                    <li key={agent.name} className={`relative min-w-0 border p-3 ${agent.tone}`}>
                      <span className="flex items-center justify-between gap-2">
                        <Icon className="h-4 w-4" />
                        <span className="font-mono text-[9px] opacity-60">0{index + 1}</span>
                      </span>
                      <p className="mt-3 text-[11px] font-semibold text-white">{agent.name}</p>
                      <p className="mt-1 text-[9px] opacity-70">{agent.output}</p>
                      {index < AGENTS.length - 1 && <ArrowRight className="absolute -right-2.5 top-1/2 z-10 hidden h-4 w-4 -translate-y-1/2 text-zinc-600 xl:block" />}
                    </li>
                  );
                })}
              </ol>
            </div>

            <div className="hidden justify-center xl:flex"><FlowArrow /></div>
            <div className="xl:w-[190px] xl:shrink-0">
              <BoundaryNode icon={Sparkles} label="Authorized output" value="Helpful action or silence" tone="green" />
            </div>
          </div>

          <div className="my-4 flex justify-center"><FlowArrow vertical /></div>

          <div className="grid items-center gap-3 border-t border-zinc-800 pt-4 md:grid-cols-[1fr_24px_1fr_24px_1fr]">
            <BoundaryNode icon={Database} label="Evidence store" value="Events, state, decisions" tone="teal" />
            <div className="hidden justify-center md:flex"><FlowArrow /></div>
            <BoundaryNode icon={GitBranch} label="Outcome attribution" value="Shown, clicked, dismissed, converted" />
            <div className="hidden justify-center md:flex"><FlowArrow /></div>
            <BoundaryNode icon={Activity} label="Learning loop" value="Experiments, affinity, drift" tone="green" />
          </div>
        </div>
      </section>

      <section className="mt-5 border-y border-zinc-800">
        <header className="flex items-center gap-2 py-3">
          <ShieldCheck className="h-4 w-4 text-amber-300" />
          <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-300">System guarantees</h2>
        </header>
        <ul className="grid border-t border-zinc-800 sm:grid-cols-2 xl:grid-cols-5">
          {GUARANTEES.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.title} className="border-b border-r border-zinc-800 px-4 py-4 xl:border-b-0">
                <Icon className="h-4 w-4 text-amber-300" />
                <p className="mt-3 text-xs font-semibold text-white">{item.title}</p>
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">{item.detail}</p>
              </li>
            );
          })}
        </ul>
      </section>

      <footer className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 border border-zinc-800 bg-[#0d1117] px-5 py-3 font-mono text-[10px] text-zinc-500">
        <span>React + Vite</span>
        <span>FastAPI modular monolith</span>
        <span>SQLite / PostgreSQL</span>
        <span>Gradient-boosted models + SHAP</span>
        <span>Local deterministic fallback</span>
        <span>SSE dashboard stream</span>
      </footer>
    </div>
  );
}
