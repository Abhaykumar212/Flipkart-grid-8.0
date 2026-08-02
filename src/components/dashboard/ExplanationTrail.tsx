import { ArrowDown, BadgeCheck, BrainCircuit, Scale, ScanSearch, Sparkles, Target } from "lucide-react";
import type { DecisionTraceResponse } from "../../types/dashboard";

export function ExplanationTrail({ trace }: { trace: DecisionTraceResponse }) {
  const steps = [
    { label: "Observed evidence", icon: ScanSearch, text: trace.explanation.observations.map((item) => item.statement).join(" ") || "No elevated evidence was required." },
    { label: "Model prediction", icon: BrainCircuit, text: trace.audit_answers.elevated_risk },
    { label: "Root-cause inference", icon: Target, text: trace.audit_answers.root_cause },
    { label: "Policy and utility", icon: Scale, text: `${trace.candidates.length} candidate records were audited. ${trace.audit_answers.discount_not_offered}` },
    { label: "Selected action", icon: Sparkles, text: trace.audit_answers.selected_intervention },
    { label: "Uncertainty", icon: BadgeCheck, text: trace.audit_answers.uncertainty },
  ];
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-center justify-between gap-3"><h2 className="text-sm font-semibold text-white">Explanation trail</h2><span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2 py-1 text-[10px] font-semibold uppercase text-cyan-300">{trace.explanation.rendered_by === "LLM" ? "LLM" : "template"}</span></div>
      <p className="mt-1 text-xs text-slate-500">Grounded statements from the persisted trace.</p>
      {trace.explanation.rendered_text && <p className="mt-4 rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-sm leading-relaxed text-slate-300">{trace.explanation.rendered_text}</p>}
      <ol className="mt-5">
        {steps.map(({ label, icon: Icon, text }, index) => (
          <li key={label}>
            <div className="flex gap-3 rounded-lg border border-slate-800 bg-slate-950/40 p-3">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-cyan-500/10"><Icon className="h-4 w-4 text-cyan-300" /></span>
              <div><p className="text-xs font-semibold uppercase tracking-wider text-slate-300">{label}</p><p className="mt-1 text-xs leading-relaxed text-slate-500">{text}</p></div>
            </div>
            {index < steps.length - 1 && <ArrowDown className="mx-auto my-1 h-4 w-4 text-slate-700" />}
          </li>
        ))}
      </ol>
      <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-300">Discount counterfactual</p>
        <p className="mt-1 text-xs text-amber-100/70">{trace.audit_answers.discount_not_offered}</p>
      </div>
      <p className="mt-4 font-mono text-[10px] text-slate-600">Versions · {Object.entries(trace.audit_answers.versions).map(([name, version]) => `${name}:${version}`).join(" · ")}</p>
    </section>
  );
}
