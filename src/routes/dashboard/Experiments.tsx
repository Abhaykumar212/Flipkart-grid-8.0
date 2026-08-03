import { useCallback, useEffect, useState } from "react";
import { FlaskConical, Loader2, Users } from "lucide-react";
import { EmptyState, PageHeader, Panel, StatTile } from "../../components/dashboard/Panel";
import { apiGet, apiPost } from "../../lib/api";
import { formatPercent, formatRupees } from "../../lib/metrics";
import type { ExperimentMetricsResponse, SimulateResponse } from "../../types/dashboard";

type Arm = ExperimentMetricsResponse["arms"][string];

const METRICS: Array<{
  key: keyof Arm;
  label: string;
  format: (value: number) => string;
  /** Whether a higher number is the better outcome for that arm. */
  higherIsBetter: boolean;
  hint?: string;
}> = [
  { key: "intervention_rate", label: "Intervened", format: (v) => formatPercent(v, 0), higherIsBetter: false, hint: "Share of sessions nudged at all" },
  { key: "ctr", label: "Engagement", format: (v) => formatPercent(v, 1), higherIsBetter: true, hint: "Clicks per nudge shown" },
  { key: "dismissal_rate", label: "Dismissed", format: (v) => formatPercent(v, 1), higherIsBetter: false, hint: "Swatted away by the shopper" },
  { key: "conversion_rate", label: "Conversion", format: (v) => formatPercent(v, 1), higherIsBetter: true },
  { key: "margin_per_session", label: "Margin / session", format: formatRupees, higherIsBetter: true },
  { key: "total_discount_cost", label: "Discount spend", format: formatRupees, higherIsBetter: false },
];

function ComparisonRow({
  label,
  hint,
  control,
  treatment,
  format,
  higherIsBetter,
}: {
  label: string;
  hint?: string;
  control: number;
  treatment: number;
  format: (value: number) => string;
  higherIsBetter: boolean;
}) {
  const max = Math.max(control, treatment, Number.EPSILON);
  const treatmentWins = higherIsBetter ? treatment > control : treatment < control;
  const tied = control === treatment;
  return (
    <div className="py-3">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-slate-300">{label}</p>
          {hint && <p className="text-[10px] text-slate-600">{hint}</p>}
        </div>
        {!tied && (
          <span
            className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
              treatmentWins ? "bg-emerald-500/15 text-emerald-300" : "bg-slate-700/50 text-slate-400"
            }`}
          >
            {treatmentWins ? "treatment" : "control"} ahead
          </span>
        )}
      </div>
      <div className="space-y-1.5">
        {[
          { name: "Control", value: control, tone: "bg-slate-500" },
          { name: "Personalized", value: treatment, tone: "bg-cyan-400" },
        ].map((row) => (
          <div key={row.name} className="flex items-center gap-3">
            <span className="w-24 shrink-0 text-[10px] uppercase tracking-wide text-slate-500">{row.name}</span>
            <span className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
              <span
                className={`block h-full rounded-full ${row.tone}`}
                style={{ width: `${Math.max(1.5, (row.value / max) * 100)}%` }}
              />
            </span>
            <span className="w-24 shrink-0 text-right font-mono text-xs text-slate-300">
              {format(row.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Experiments() {
  const [data, setData] = useState<ExperimentMetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [simulating, setSimulating] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await apiGet<ExperimentMetricsResponse>("/api/v1/dashboard/experiments/EXP-001/metrics"));
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load experiment metrics");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const simulate = useCallback(async () => {
    setSimulating(true);
    try {
      await apiPost<SimulateResponse>("/api/v1/demo/simulate", { sessions: 40 });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Simulation failed");
    } finally {
      setSimulating(false);
    }
  }, [load]);

  if (error) {
    return (
      <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-5 text-rose-200">
        {error}
      </div>
    );
  }
  if (!data) return <div className="h-64 animate-pulse rounded-lg bg-slate-900" />;

  const control = data.arms[data.experiment.control_group];
  const treatment = data.arms[data.experiment.treatment_group];
  const totalSessions = control.sessions + treatment.sessions;
  const uplift = data.uplift;

  const simulateButton = (
    <button
      type="button"
      onClick={() => void simulate()}
      disabled={simulating}
      className="inline-flex items-center gap-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-200 hover:bg-cyan-500/20 disabled:opacity-50"
    >
      {simulating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Users className="h-3.5 w-3.5" />}
      Generate 40 sessions
    </button>
  );

  return (
    <div>
      <PageHeader
        eyebrow={data.experiment.experiment_id}
        title={data.experiment.name}
        description={`Deterministic ${data.experiment.traffic_split}/${100 - data.experiment.traffic_split} split by session hash. Control applies one fixed wishlist reminder to every session; the treatment arm runs the full diagnosis-and-policy path.`}
        action={simulateButton}
      />

      {totalSessions === 0 ? (
        <EmptyState
          icon={<FlaskConical className="mx-auto h-8 w-8" />}
          title="No sessions assigned to this experiment yet"
          action={simulateButton}
        >
          Assignment happens the first time a session reaches a decision. Browse the storefront, run a
          scenario, or generate synthetic traffic to populate both arms.
        </EmptyState>
      ) : (
        <>
          <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile
              label="Conversion uplift"
              value={`${uplift.absolute >= 0 ? "+" : ""}${(uplift.absolute * 100).toFixed(2)} pp`}
              tone={uplift.label === "significant" ? (uplift.absolute > 0 ? "good" : "bad") : "default"}
              hint={uplift.ci95 !== null ? `95% CI ±${(uplift.ci95 * 100).toFixed(2)} pp` : "Interval unavailable"}
            />
            <StatTile
              label="Verdict"
              value={uplift.label}
              tone={uplift.label === "significant" ? "good" : "warn"}
              hint={
                uplift.label === "significant"
                  ? "Difference exceeds the confidence interval"
                  : "Not yet separable from noise"
              }
            />
            <StatTile
              label="Sessions"
              value={totalSessions.toLocaleString("en-IN")}
              hint={`${control.sessions} control · ${treatment.sessions} treatment`}
            />
            <StatTile
              label="Engagement gap"
              value={`${((treatment.ctr - control.ctr) * 100).toFixed(1)} pp`}
              tone={treatment.ctr > control.ctr ? "good" : "default"}
              hint="Cause-matched vs generic nudges"
            />
          </section>

          <div className="grid gap-5 xl:grid-cols-[1.3fr_1fr]">
            <Panel
              title="Arm comparison"
              subtitle="Control nudges everyone with the same reminder. Treatment diagnoses first and may stay silent."
            >
              <div className="divide-y divide-slate-800">
                {METRICS.map((metric) => (
                  <ComparisonRow
                    key={String(metric.key)}
                    label={metric.label}
                    hint={metric.hint}
                    control={Number(control[metric.key] ?? 0)}
                    treatment={Number(treatment[metric.key] ?? 0)}
                    format={metric.format}
                    higherIsBetter={metric.higherIsBetter}
                  />
                ))}
              </div>
            </Panel>

            <Panel title="How to read this" subtitle="What the arms are actually testing.">
              <div className="space-y-4 text-xs leading-relaxed text-slate-400">
                <p>
                  <span className="font-semibold text-white">The hypothesis.</span> A nudge that
                  addresses the diagnosed reason for hesitation earns more engagement and less
                  irritation than a blanket reminder, while spending less.
                </p>
                <p>
                  <span className="font-semibold text-white">Why intervening less can win.</span> The
                  treatment arm deliberately says nothing on low-risk sessions. Those shoppers were
                  going to convert anyway, so a nudge only risks annoying them.
                </p>
                <p>
                  <span className="font-semibold text-white">Discount spend.</span>{" "}
                  {treatment.total_discount_cost === 0
                    ? "No discount has cleared its five safety conditions, so margin is fully intact."
                    : `${formatRupees(treatment.total_discount_cost)} granted under policy.`}
                </p>
                <p className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-amber-100/70">
                  Figures from synthetic traffic are measured from a documented shopper-response model
                  applied to real pipeline decisions. They demonstrate the experiment machinery; they
                  are not evidence of production uplift.
                </p>
              </div>
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}
