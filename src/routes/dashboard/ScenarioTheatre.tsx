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
  INTERVENE: "bg-cyan-500/15 text-cyan-300 border-cyan-500/25",
  NO_ACTION: "bg-slate-700/40 text-slate-300 border-slate-600/40",
  ABSTAIN: "bg-amber-500/15 text-amber-300 border-amber-500/25",
};

function StepRow({ step }: { step: ScenarioStep }) {
  const expected = Object.entries(step.expected);
  return (
    <li className="rounded-lg border border-slate-800 bg-slate-950/50 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded border px-2 py-0.5 text-[10px] font-semibold uppercase ${
            DECISION_TONE[step.decision ?? ""] ?? "border-slate-700 bg-slate-800 text-slate-300"
          }`}
        >
          {step.decision}
        </span>
        <span className="text-sm font-medium text-white">
          {titleCase(step.intervention ?? "No action")}
        </span>
        {step.experiment_group && (
          <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-slate-400">
            {step.experiment_group}
          </span>
        )}
        {step.passed ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-400" aria-label="Matched expectation" />
        ) : (
          <XCircle className="h-4 w-4 text-rose-400" aria-label="Did not match expectation" />
        )}
        {step.decision_id && (
          <Link
            to={`/dashboard/decisions/${step.decision_id}`}
            className="ml-auto inline-flex items-center gap-1 text-xs text-cyan-300 hover:text-cyan-200"
          >
            Open full trace
            <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        )}
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs sm:grid-cols-4">
        <div>
          <dt className="text-slate-500">Root cause</dt>
          <dd className="text-slate-300">{titleCase(step.dominant_cause ?? "—")}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Probability</dt>
          <dd className="font-mono text-slate-300">
            {step.probability === null ? "—" : `${Math.min(99, Math.round(step.probability * 100))}%`}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Confidence</dt>
          <dd className="font-mono text-slate-300">
            {step.confidence === null ? "—" : `${(step.confidence * 100).toFixed(0)}%`}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Trigger</dt>
          <dd className="text-slate-300">{titleCase(step.trigger)}</dd>
        </div>
      </dl>

      {step.rendered_text && (
        <p className="mt-3 rounded border border-slate-800 bg-slate-900/60 p-2.5 text-xs leading-relaxed text-slate-400">
          {step.rendered_text}
        </p>
      )}

      {expected.length > 0 && (
        <p className="mt-2 text-[11px] text-slate-600">
          Expected {expected.map(([key, value]) => `${key}=${value}`).join(", ")}
        </p>
      )}
      {!step.passed && (
        <p className="mt-2 rounded border border-rose-500/25 bg-rose-500/10 p-2 text-[11px] text-rose-200">
          {Object.entries(step.mismatches)
            .map(([key, item]) => `${key}: expected ${item.expected}, got ${item.actual}`)
            .join(" · ")}
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
    <article className="rounded-xl border border-slate-800 bg-slate-900">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 px-5 py-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-cyan-500/15 font-mono text-sm font-bold text-cyan-300">
              {scenario.scenario}
            </span>
            <h2 className="text-sm font-semibold text-white">{scenario.title}</h2>
            {result && (
              <span
                className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
                  result.passed
                    ? "bg-emerald-500/15 text-emerald-300"
                    : "bg-rose-500/15 text-rose-300"
                }`}
              >
                {result.passed ? "passed" : "failed"}
              </span>
            )}
          </div>
          <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-cyan-300/80">
            Proves: {scenario.proves}
          </p>
          <p className="mt-1.5 max-w-2xl text-xs leading-relaxed text-slate-400">{scenario.detail}</p>
          <p className="mt-2 font-mono text-[10px] text-slate-600">
            {scenario.session_count} session{scenario.session_count === 1 ? "" : "s"} ·{" "}
            {scenario.event_count} events
            {result ? ` · ${result.duration_ms.toFixed(0)} ms` : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={onRun}
          disabled={running}
          className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-500/20 disabled:opacity-50"
        >
          {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
          {running ? "Running" : result ? "Run again" : "Run scenario"}
        </button>
      </header>
      {result && (
        <ol className="space-y-2 p-4">
          {result.steps.map((step, index) => (
            <StepRow key={`${step.decision_id ?? index}`} step={step} />
          ))}
        </ol>
      )}
    </article>
  );
}

export default function ScenarioTheatre() {
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
      const result = await apiPost<ScenarioRunResponse>(
        `/api/v1/demo/scenarios/${letter}/run`,
        {},
      );
      setResults((current) => ({ ...current, [letter]: result }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Scenario run failed");
    } finally {
      setRunning(null);
    }
  }, []);

  const runAll = useCallback(async () => {
    setRunningAll(true);
    for (const scenario of scenarios) {
      await run(scenario.scenario);
    }
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

  return (
    <div>
      <PageHeader
        eyebrow="Proof scenarios"
        title="Scenario theatre"
        description="Eight frozen scenarios replayed through the live decision path — the same code that serves the storefront. Each states what it is meant to prove, then shows what actually happened."
        action={
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void simulate()}
              disabled={simulating}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300 hover:border-slate-600 hover:text-white disabled:opacity-50"
            >
              {simulating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Users className="h-3.5 w-3.5" />}
              Generate 40 sessions
            </button>
            <button
              type="button"
              onClick={() => void runAll()}
              disabled={runningAll || scenarios.length === 0}
              className="inline-flex items-center gap-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-200 hover:bg-cyan-500/20 disabled:opacity-50"
            >
              {runningAll ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              Run all eight
            </button>
          </div>
        }
      />

      {error && (
        <div role="alert" className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      )}

      {completed.length > 0 && (
        <div className="mb-6 grid gap-3 sm:grid-cols-3">
          <StatTile label="Scenarios run" value={`${completed.length} / ${scenarios.length}`} />
          <StatTile
            label="Matching expectations"
            value={`${passed} / ${completed.length}`}
            tone={passed === completed.length ? "good" : "bad"}
          />
          <StatTile
            label="Slowest run"
            value={`${Math.max(...completed.map((item) => item.duration_ms)).toFixed(0)} ms`}
          />
        </div>
      )}

      {simulation && (
        <Panel
          title="Synthetic traffic generated"
          subtitle={simulation.disclaimer}
          className="mb-6"
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <StatTile label="Sessions" value={simulation.totals.sessions} />
            <StatTile label="Decisions" value={simulation.totals.decisions} />
            <StatTile label="Nudges shown" value={simulation.totals.shown} />
            <StatTile label="Engaged" value={simulation.totals.clicked} tone="good" />
            <StatTile label="Converted" value={simulation.totals.converted} tone="good" />
          </div>
          <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-300">
              <AlertTriangle className="mr-1 inline h-3 w-3" />
              Stated assumptions
            </p>
            <p className="mt-1.5 text-xs leading-relaxed text-amber-100/70">
              Shopper baselines come from each session&rsquo;s own calibrated risk. A cause-matched nudge
              is assumed to be engaged {formatPercent(Number(simulation.response_model.matched_click), 0)} of
              the time versus {formatPercent(Number(simulation.response_model.generic_click), 0)} for a
              generic one, and dismissal carries a conversion penalty. That asymmetry is the hypothesis
              under test, not a measured result.
            </p>
          </div>
          <p className="mt-3 text-right">
            <Link to="/dashboard/experiments" className="text-xs text-cyan-300 hover:text-cyan-200">
              See the A/B outcome →
            </Link>
          </p>
        </Panel>
      )}

      {scenarios.length === 0 && !error ? (
        <EmptyState title="Loading scenarios…" />
      ) : (
        <div className="space-y-4">
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
