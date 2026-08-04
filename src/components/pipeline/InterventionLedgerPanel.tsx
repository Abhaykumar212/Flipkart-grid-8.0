import { useSyncExternalStore } from "react";
import { Ban, Gauge, IndianRupee, ListTree, ThumbsDown, ThumbsUp } from "lucide-react";
import { fatigueBudget, MAX_SESSION_EXPOSURE } from "../../lib/fatigueBudget";
import { interventionLedger } from "../../lib/interventionLedger";
import { RUNG3_ASSUMED_VALUE_INR } from "../../lib/interventionPolicy";

const RUNG_LABELS = ["Rung 0 · passive", "Rung 1 · ambient", "Rung 2 · active", "Rung 3 · costly"];

const NO_INTERVENTION_LABELS: Record<string, string> = {
  gate_held: "Gate held (below RCA threshold)",
  low_confidence: "Low confidence",
  margin_approval_required: "Rung-3 blocked — margin approval",
  fatigue_cap: "Fatigue cap hit",
  cooldown: "Cooldown active",
  no_lever_above_threshold: "No lever above threshold",
};

/**
 * Session-scoped accumulator across every run this session — complements the
 * live "Delivery policy" section above it (which shows the current budget
 * state) with what's happened cumulatively: what shipped, what was withheld
 * and why, and the promotional spend that policy avoided by not shipping
 * every rung-3 lever it considered.
 */
export function InterventionLedgerPanel() {
  const fatigue = useSyncExternalStore(fatigueBudget.subscribe, fatigueBudget.getSnapshot);
  const ledger = useSyncExternalStore(interventionLedger.subscribe, interventionLedger.getSnapshot);

  const byRung = [0, 1, 2, 3].map(
    (rung) => fatigue.exposures.filter((exposure) => exposure.intensity === rung).length,
  );
  const accepted = fatigue.exposures.filter((exposure) => exposure.outcome === "accepted").length;
  const dismissed = fatigue.exposures.filter((exposure) => exposure.outcome === "dismissed").length;
  const ignored = fatigue.exposures.filter((exposure) => exposure.outcome === "pending").length;

  const heldEntries = Object.entries(ledger.heldByReason);
  const spendEntries = Object.entries(ledger.spendAvoidedByLever);

  return (
    <section data-testid="intervention-ledger" className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">Intervention ledger</h2>
          <p className="text-xs text-slate-500">
            Accumulates across every run this session — what shipped, what was held, and what it saved.
          </p>
        </div>
        <button
          onClick={() => interventionLedger.reset()}
          className="ml-auto rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
        >
          Reset ledger
        </button>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-100 p-3">
          <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <ListTree className="h-3.5 w-3.5" />
            Shown, by rung
          </h3>
          <ul className="mt-2 flex flex-col gap-1.5">
            {RUNG_LABELS.map((label, rung) => (
              <li key={label} className="flex items-center justify-between text-xs text-slate-700">
                <span>{label}</span>
                <span className="font-semibold tabular-nums">{byRung[rung]}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-lg border border-slate-100 p-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Outcomes</h3>
          <ul className="mt-2 flex flex-col gap-1.5 text-xs text-slate-700">
            <li className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-emerald-700">
                <ThumbsUp className="h-3.5 w-3.5" /> Accepted
              </span>
              <span className="font-semibold tabular-nums">{accepted}</span>
            </li>
            <li className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-red-600">
                <ThumbsDown className="h-3.5 w-3.5" /> Dismissed
              </span>
              <span className="font-semibold tabular-nums">{dismissed}</span>
            </li>
            <li className="flex items-center justify-between">
              <span className="text-slate-500">Ignored so far</span>
              <span className="font-semibold tabular-nums">{ignored}</span>
            </li>
          </ul>
        </div>

        <div className="rounded-lg border border-slate-100 p-3">
          <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <Ban className="h-3.5 w-3.5" />
            Do-nothing decisions
          </h3>
          {heldEntries.length === 0 ? (
            <p className="mt-2 text-xs text-slate-400">None recorded yet this session.</p>
          ) : (
            <ul className="mt-2 flex flex-col gap-1.5 text-xs text-slate-700">
              {heldEntries.map(([reason, count]) => (
                <li key={reason} className="flex items-center justify-between">
                  <span>{NO_INTERVENTION_LABELS[reason] ?? reason}</span>
                  <span className="font-semibold tabular-nums">{count}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-slate-100 p-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Decision source (Asked vs Inferred)</h3>
          <ul className="mt-2 flex flex-col gap-1.5 text-xs text-slate-700">
            <li className="flex items-center justify-between">
              <span>We inferred (model diagnosis)</span>
              <span className="font-semibold tabular-nums">{ledger.inferredCount ?? 0}</span>
            </li>
            <li className="flex items-center justify-between">
              <span>We asked (user elicitation)</span>
              <span className="font-semibold tabular-nums">{ledger.elicitationCount ?? 0}</span>
            </li>
          </ul>
        </div>

        <div className="rounded-lg border border-slate-100 p-3">
          <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <Gauge className="h-3.5 w-3.5" />
            Fatigue budget
          </h3>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-lg font-bold tabular-nums text-slate-900">{fatigue.decayedExposure}</span>
            <span className="text-xs text-slate-500">/ {MAX_SESSION_EXPOSURE} (decayed)</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-blue-500"
              style={{ width: `${Math.min(100, (fatigue.decayedExposure / MAX_SESSION_EXPOSURE) * 100)}%` }}
            />
          </div>
          <p className="mt-1.5 text-[11px] text-slate-400">Recovers over time — a 4-minute half-life per exposure.</p>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50/60 p-3">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-emerald-800">
          <IndianRupee className="h-3.5 w-3.5" />
          Estimated promotional spend avoided
        </h3>
        <p className="mt-1 text-2xl font-bold tabular-nums text-emerald-900">
          ₹{ledger.spendAvoidedInr.toLocaleString("en-IN")}
        </p>
        <p className="mt-1 text-[11px] text-emerald-800/80">
          Counts every rung-3 (costly) lever the ranking considered as a candidate and then suppressed
          by policy — confidence gate, missing margin approval, fatigue, or escalation not having
          reached it yet — not levers that were simply never relevant to the diagnosis.
        </p>
        <p className="mt-2 text-[11px] text-slate-500">
          Assumes{" "}
          {Object.entries(RUNG3_ASSUMED_VALUE_INR)
            .map(([leverId, value]) => `₹${value} avg ${leverId}`)
            .join(", ")}{" "}
          — nominal, not measured lift.
        </p>
        {spendEntries.length > 0 && (
          <ul className="mt-2 flex flex-col gap-1 border-t border-emerald-100 pt-2">
            {spendEntries.map(([leverId, entry]) => (
              <li key={leverId} className="flex items-center justify-between text-xs text-emerald-900">
                <span className="font-mono text-[11px]">{leverId}</span>
                <span className="tabular-nums">
                  {entry.count} × ₹{entry.assumedUnitValueInr} = ₹{entry.totalInr.toLocaleString("en-IN")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
