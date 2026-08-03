import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Loader2,
  Play,
  Users,
  XCircle,
} from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState, PageHeader, Panel, StatTile } from "../../components/dashboard/Panel";
import { apiGet, apiPost } from "../../lib/api";
import { formatPercent, titleCase } from "../../lib/metrics";
import type {
  DemoScenario,
  ScenarioRunResponse,
  ScenarioStep,
  SimulateResponse,
} from "../../types/dashboard";

const DECISION_TONE: Record<string, string> = {
  INTERVENE: "border-teal-400/30 bg-teal-400/10 text-teal-200",
  NO_ACTION: "border-zinc-600 bg-zinc-700/30 text-zinc-300",
  ABSTAIN: "border-amber-400/30 bg-amber-400/10 text-amber-200",
};

function ResultRow({ step }: { step: ScenarioStep }) {
  return (
    <li className="border-t border-zinc-800 px-4 py-3">
      <div className="flex items-center gap-2">
        <span className={`rounded border px-1.5 py-0.5 text-[9px] font-semibold ${
          DECISION_TONE[step.decision ?? ""] ?? DECISION_TONE.NO_ACTION
        }`}>
          {step.decision ?? "NO RESULT"}
        </span>
        <span className="min-w-0 flex-1 truncate text-xs font-medium text-white">
          {titleCase(step.intervention ?? "No action")}
        </span>
        {step.passed ? (
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" aria-label="Matched expectation" />
        ) : (
          <XCircle className="h-4 w-4 shrink-0 text-rose-400" aria-label="Did not match expectation" />
        )}
        {step.decision_id && (
          <Link
            to={`/dashboard/decisions/${step.decision_id}`}
            aria-label="Open full decision trace"
            title="Open full decision trace"
            className="text-blue-300 hover:text-blue-200"
          >
            <ChevronRight className="h-4 w-4" />
          </Link>
        )}
      </div>
      <p className="mt-2 truncate text-[10px] text-zinc-500">
        {titleCase(step.dominant_cause ?? "Unknown")} / {step.probability === null ? "No score" : `${Math.min(99, Math.round(step.probability * 100))}% risk`}
        {step.experiment_group ? ` / ${step.experiment_group}` : ""}
      </p>
      {step.rendered_text && <p className="mt-2 line-clamp-2 text-[10px] leading-relaxed text-zinc-500">{step.rendered_text}</p>}
      {!step.passed && (
        <p className="mt-2 border border-rose-500/25 bg-rose-500/10 p-2 text-[10px] text-rose-200">
          {Object.entries(step.mismatches)
            .map(([key, item]) => `${key}: expected ${item.expected}, got ${item.actual}`)
            .join(" / ")}
        </p>
      )}
    </li>
  );
}

function ScenarioCard({
  scenario,
  result,
  running,
  onRun,
}: {
  scenario: DemoScenario;
  result?: ScenarioRunResponse;
  running: boolean;
  onRun: () => void;
}) {
  return (
    <article className="flex min-h-[228px] flex-col border border-zinc-800 bg-[#0d1117]">
      <header className="flex flex-1 flex-col px-4 py-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-blue-500/15 font-mono text-sm font-bold text-blue-300">
              {scenario.scenario}
            </span>
            <h3 className="min-w-0 flex-1 truncate text-sm font-semibold text-white" title={scenario.title}>{scenario.title}</h3>
            {result && (
              <span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase ${
                result.passed ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"
              }`}>
                {result.passed ? "passed" : "failed"}
              </span>
            )}
          </div>
          <p className="mt-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-teal-300">{scenario.proves}</p>
          <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-zinc-500">{scenario.detail}</p>
        </div>

        <div className="mt-4 flex items-center justify-between gap-3 border-t border-zinc-800 pt-3">
          <p className="font-mono text-[9px] text-zinc-600">
            {scenario.session_count} session{scenario.session_count === 1 ? "" : "s"} / {scenario.event_count} events
            {result ? ` / ${result.duration_ms.toFixed(0)} ms` : ""}
          </p>
          <button
            type="button"
            onClick={onRun}
            disabled={running}
            className="inline-flex h-8 shrink-0 cursor-pointer items-center gap-1.5 border border-blue-400/35 bg-blue-400/10 px-2.5 text-[10px] font-semibold text-blue-200 transition hover:bg-blue-400/20 disabled:opacity-50"
          >
            {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
            {running ? "Running" : result ? "Run again" : "Run"}
          </button>
        </div>
      </header>
      {result && <ol>{result.steps.map((step, index) => <ResultRow key={step.decision_id ?? index} step={step} />)}</ol>}
    </article>
  );
}

function ActionButtons({
  simulating,
  runningAll,
  disabled,
  onSimulate,
  onRunAll,
}: {
  simulating: boolean;
  runningAll: boolean;
  disabled: boolean;
  onSimulate: () => void;
  onRunAll: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={onSimulate}
        disabled={simulating}
        className="inline-flex h-9 cursor-pointer items-center gap-2 border border-zinc-700 bg-[#0d1117] px-3 text-xs text-zinc-300 hover:border-zinc-500 hover:text-white disabled:opacity-50"
      >
        {simulating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Users className="h-3.5 w-3.5" />}
        Generate 40 sessions
      </button>
      <button
        type="button"
        onClick={onRunAll}
        disabled={runningAll || disabled}
        className="inline-flex h-9 cursor-pointer items-center gap-2 border border-blue-400/35 bg-blue-400/10 px-3 text-xs font-semibold text-blue-200 hover:bg-blue-400/20 disabled:opacity-50"
      >
        {runningAll ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
        Run all eight
      </button>
    </div>
  );
}

export default function ScenarioTheatre({ embedded = false }: { embedded?: boolean }) {
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [results, setResults] = useState<Record<string, ScenarioRunResponse>>({});
  const [running, setRunning] = useState<string | null>(null);
  const [runningAll, setRunningAll] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [simulation, setSimulation] = useState<SimulateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiGet<{ scenarios: DemoScenario[] }>("/api/v1/demo/scenarios")
      .then((response) => setScenarios(response.scenarios))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load scenarios"));
  }, []);

  const run = useCallback(async (letter: string) => {
    setRunning(letter);
    setError(null);
    try {
      const result = await apiPost<ScenarioRunResponse>(`/api/v1/demo/scenarios/${letter}/run`, {});
      setResults((current) => ({ ...current, [letter]: result }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Scenario run failed");
    } finally {
      setRunning(null);
    }
  }, []);

  const runAll = useCallback(async () => {
    setRunningAll(true);
    for (const scenario of scenarios) await run(scenario.scenario);
    setRunningAll(false);
  }, [run, scenarios]);

  const simulate = useCallback(async () => {
    setSimulating(true);
    setError(null);
    try {
      setSimulation(await apiPost<SimulateResponse>("/api/v1/demo/simulate", { sessions: 40 }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Simulation failed");
    } finally {
      setSimulating(false);
    }
  }, []);

  const completed = Object.values(results);
  const passed = completed.filter((item) => item.passed).length;
  const actions = (
    <ActionButtons
      simulating={simulating}
      runningAll={runningAll}
      disabled={scenarios.length === 0}
      onSimulate={() => void simulate()}
      onRunAll={() => void runAll()}
    />
  );

  return (
    <div>
      {embedded ? (
        <header className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Eight deterministic cases</h2>
            <p className="mt-1 text-sm text-zinc-500">Every case executes the governed path used by the storefront.</p>
          </div>
          {actions}
        </header>
      ) : (
        <PageHeader
          eyebrow="Proof scenarios"
          title="Scenario theatre"
          description="Eight frozen scenarios replayed through the live decision path."
          action={actions}
        />
      )}

      {error && <div role="alert" className="mb-4 border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div>}

      {completed.length > 0 && (
        <div className="mb-5 grid gap-3 sm:grid-cols-3">
          <StatTile label="Scenarios run" value={`${completed.length} / ${scenarios.length}`} />
          <StatTile label="Matching expectations" value={`${passed} / ${completed.length}`} tone={passed === completed.length ? "good" : "bad"} />
          <StatTile label="Slowest run" value={`${Math.max(...completed.map((item) => item.duration_ms)).toFixed(0)} ms`} />
        </div>
      )}

      {simulation && (
        <Panel title="Synthetic traffic generated" subtitle={simulation.disclaimer} className="mb-5">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <StatTile label="Sessions" value={simulation.totals.sessions} />
            <StatTile label="Decisions" value={simulation.totals.decisions} />
            <StatTile label="Nudges shown" value={simulation.totals.shown} />
            <StatTile label="Engaged" value={simulation.totals.clicked} tone="good" />
            <StatTile label="Converted" value={simulation.totals.converted} tone="good" />
          </div>
          <div className="mt-4 border border-amber-500/20 bg-amber-500/5 p-3">
            <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-amber-300">
              <AlertTriangle className="h-3.5 w-3.5" /> Stated assumptions
            </p>
            <p className="mt-1.5 text-xs leading-relaxed text-amber-100/70">
              A cause-matched nudge is assumed to be engaged {formatPercent(Number(simulation.response_model.matched_click), 0)} of the time versus {formatPercent(Number(simulation.response_model.generic_click), 0)} for a generic action. This is the hypothesis under test, not a measured production result.
            </p>
          </div>
        </Panel>
      )}

      {scenarios.length === 0 && !error ? (
        <EmptyState title="Loading scenarios..." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {scenarios.map((scenario) => (
            <ScenarioCard
              key={scenario.scenario}
              scenario={scenario}
              result={results[scenario.scenario]}
              running={running === scenario.scenario}
              onRun={() => void run(scenario.scenario)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
