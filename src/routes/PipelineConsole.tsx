import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { RefreshCw, Trash2, Workflow } from "lucide-react";
import { useCart } from "../context/CartContext";
import { useTracker } from "../context/TrackerContext";
import { pipelineTrace, runDurationMs, type PipelineRun } from "../lib/pipelineTrace";
import { sessionTracker } from "../lib/tracker";
import { DEMO_SCENARIOS, type DemoScenario } from "../data/demoScenarios";
import { TraceWaterfall } from "../components/pipeline/TraceWaterfall";
import { RcaReport } from "../components/pipeline/RcaReport";
import { ScenarioPicker } from "../components/pipeline/ScenarioPicker";

const STATUS_CHIP: Record<string, string> = {
  success: "bg-emerald-100 text-emerald-700",
  gate_not_met: "bg-slate-100 text-slate-600",
  rate_limited: "bg-amber-100 text-amber-700",
  not_configured: "bg-amber-100 text-amber-700",
  error: "bg-red-100 text-red-700",
  running: "bg-blue-100 text-blue-700",
};

const STATUS_LABEL: Record<string, string> = {
  success: "analysed",
  gate_not_met: "gate held",
  rate_limited: "rate limited",
  not_configured: "not configured",
  error: "error",
  running: "running",
};

interface PipelineConfig {
  rca_threshold: number;
  cooldown_seconds: number;
  max_per_session: number;
  rca_model: string;
  reasoning_effort: string;
  groq_configured: boolean;
}

export default function PipelineConsole() {
  const runs = useSyncExternalStore(pipelineTrace.subscribe, pipelineTrace.getSnapshot);
  const { runRootCauseAnalysis, rootCauseLoading, prediction } = useTracker();
  const { clearCart, addItem } = useCart();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [config, setConfig] = useState<PipelineConfig | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/pipeline-config")
      .then((r) => (r.ok ? r.json() : null))
      .then(setConfig)
      .catch(() => setConfig(null));
  }, []);

  // Follow the newest run unless the user has pinned an older one.
  const selected: PipelineRun | null =
    runs.find((run) => run.id === selectedId) ?? runs[0] ?? null;

  const applyScenario = useCallback(
    async (scenario: DemoScenario) => {
      setActiveScenario(scenario.id);

      // Rebuild the cart with a backdated addedAt so the run clears the
      // server-side warm-up gate immediately instead of waiting 10s.
      clearCart();
      const backdated = new Date(Date.now() - scenario.cartAgeSeconds * 1000).toISOString();
      scenario.cart.forEach(({ productId, quantity }) => {
        addItem(productId, quantity, backdated);
      });

      sessionTracker.resetScenario();
      sessionTracker.applyScenario(scenario.history, scenario.session);

      // Let the cart effect propagate into the tracker before scoring.
      await new Promise((resolve) => setTimeout(resolve, 350));

      // Deliberately NOT forced. Scenarios backdate the cart (clearing the
      // warm-up check) and change the feature signature (clearing dedup), so
      // the only thing left deciding is the probability threshold — which is
      // exactly what the low-risk preset is meant to demonstrate. Forcing here
      // would bypass that check and make the gate look decorative.
      await runRootCauseAnalysis({ scenarioLabel: scenario.label });
    },
    [addItem, clearCart, runRootCauseAnalysis],
  );

  return (
    <div className="flex flex-col gap-3">
      <header className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white">
            <Workflow className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-lg font-bold text-slate-900">Agent pipeline console</h1>
            <p className="text-xs text-slate-500">
              Live trace of every stage: session telemetry → feature engineering → XGBoost → SHAP →
              risk gate → root cause agent
            </p>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => runRootCauseAnalysis({ force: true })}
              disabled={rootCauseLoading}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${rootCauseLoading ? "animate-spin" : ""}`} />
              Re-run analysis
            </button>
            <button
              onClick={() => {
                pipelineTrace.clear();
                setSelectedId(null);
              }}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear
            </button>
          </div>
        </div>

        {config && (
          <dl className="mt-4 grid grid-cols-2 gap-2 border-t border-slate-100 pt-3 text-xs sm:grid-cols-3 lg:grid-cols-6">
            {[
              ["Trigger threshold", `${(config.rca_threshold * 100).toFixed(0)}%`],
              ["Cooldown", `${config.cooldown_seconds}s`],
              ["Session cap", `${config.max_per_session}`],
              ["Agent model", config.rca_model.split("/").pop() ?? config.rca_model],
              ["Reasoning", config.reasoning_effort],
              ["Live risk", prediction ? `${(prediction.abandonment_probability * 100).toFixed(1)}%` : "—"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 px-3 py-2">
                <dt className="text-[10px] uppercase tracking-wide text-slate-500">{label}</dt>
                <dd className="mt-0.5 font-semibold text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>
        )}

        {config && !config.groq_configured && (
          <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            GROQ_API_KEY is not set — the pipeline will run through the risk gate but skip the agent.
            Copy <code>.env.example</code> to <code>.env</code> and add a key.
          </p>
        )}
      </header>

      <ScenarioPicker
        activeId={activeScenario}
        busy={rootCauseLoading}
        onRun={(scenario) => void applyScenario(scenario)}
      />

      <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[300px_1fr]">
        {/* Run history */}
        <aside className="rounded-xl border border-slate-200 bg-white">
          <header className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-800">Runs</h2>
          </header>
          {runs.length === 0 ? (
            <p className="px-4 py-8 text-center text-xs text-slate-500">
              No runs yet. Pick a scenario above, or add items to your cart and let the auto-trigger
              fire.
            </p>
          ) : (
            <ul className="max-h-[520px] overflow-y-auto">
              {runs.map((run) => {
                const isSelected = selected?.id === run.id;
                return (
                  <li key={run.id}>
                    <button
                      onClick={() => setSelectedId(run.id)}
                      className={`w-full border-b border-slate-100 px-4 py-3 text-left last:border-0 ${
                        isSelected ? "bg-blue-50" : "hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${STATUS_CHIP[run.status]}`}
                        >
                          {STATUS_LABEL[run.status]}
                        </span>
                        <span className="ml-auto text-[10px] text-slate-400">
                          {new Date(run.startedAt).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="mt-1 flex items-baseline gap-2">
                        <span className="text-sm font-bold tabular-nums text-slate-900">
                          {run.probability !== null
                            ? `${(run.probability * 100).toFixed(1)}%`
                            : "—"}
                        </span>
                        <span className="text-[11px] text-slate-500">
                          {run.scenarioLabel ?? (run.trigger === "manual" ? "manual" : "auto")}
                        </span>
                        <span className="ml-auto text-[10px] tabular-nums text-slate-400">
                          {runDurationMs(run).toFixed(0)}ms
                        </span>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </aside>

        {/* Selected run */}
        <div className="flex flex-col gap-3">
          {selected ? (
            <>
              <TraceWaterfall run={selected} />
              <RcaReport run={selected} />
            </>
          ) : (
            <section className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
              <Workflow className="mx-auto h-10 w-10 text-slate-300" />
              <p className="mt-3 text-sm text-slate-600">
                Run a scenario to see the pipeline execute end to end.
              </p>
              <p className="mt-1 text-xs text-slate-400">
                {DEMO_SCENARIOS.length} presets available, including one that demonstrates the gate
                correctly declining to call the agent.
              </p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
