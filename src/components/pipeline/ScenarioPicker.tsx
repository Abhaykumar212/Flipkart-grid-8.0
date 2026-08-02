import { Play } from "lucide-react";
import { DEMO_SCENARIOS, type DemoScenario } from "../../data/demoScenarios";

interface ScenarioPickerProps {
  activeId: string | null;
  busy: boolean;
  onRun: (scenario: DemoScenario) => void;
}

export function ScenarioPicker({ activeId, busy, onRun }: ScenarioPickerProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-800">Demo scenarios</h2>
      <p className="mt-1 text-xs text-slate-500">
        Each preset loads a cart and shopper profile that deterministically produces a specific
        outcome, so the pipeline can be demonstrated on demand.
      </p>

      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {DEMO_SCENARIOS.map((scenario) => {
          const isActive = scenario.id === activeId;
          return (
            <button
              key={scenario.id}
              onClick={() => onRun(scenario)}
              disabled={busy}
              className={`group flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
                isActive
                  ? "border-blue-400 bg-blue-50 ring-1 ring-blue-300"
                  : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <span className="flex w-full items-center gap-2">
                <span
                  className={`h-2 w-2 shrink-0 rounded-full bg-gradient-to-r ${scenario.accent}`}
                />
                <span className="text-sm font-semibold text-slate-800">{scenario.label}</span>
                <Play className="ml-auto h-3.5 w-3.5 text-slate-400 group-hover:text-blue-600" />
              </span>
              <span className="text-[11px] leading-snug text-slate-500">{scenario.intent}</span>
              <span className="mt-0.5 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                {scenario.expectedOutcome}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
