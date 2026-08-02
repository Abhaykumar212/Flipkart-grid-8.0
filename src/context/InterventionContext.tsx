import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useLocation } from "react-router-dom";
import { useTracker } from "./TrackerContext";
import { sendInterventionFeedback } from "../lib/tracker";
import { fatigueBudget } from "../lib/fatigueBudget";
import {
  assertPolicyCoverage,
  findSuppressedRung3Levers,
  resolveMarginApproval,
  selectSurface,
  type Intensity,
  type InterventionSurface,
  type SelectedIntervention,
  type SelectSurfaceOptions,
} from "../lib/interventionPolicy";
import { LEVER_TARGET_KEYS } from "../lib/interventionTargets";
import { getAllMounted } from "../lib/targetRegistry";
import { pipelineTrace, type DeliveryDecision, type RecommendedIntervention } from "../lib/pipelineTrace";
import { interventionLedger } from "../lib/interventionLedger";

/**
 * Delivery layer between the Phase 3 intervention plan and the screen.
 *
 * The pipeline hands over a ranked plan; this decides whether any of it is worth
 * the shopper's attention right now, at what intensity, and on which surface —
 * then hands exactly one intervention (or nothing) to whatever renders it.
 *
 * Everything upstream of here is about *value*. Everything here is about *cost*.
 */

interface InterventionContextValue {
  active: RecommendedIntervention | null;
  surface: InterventionSurface | null;
  intensity: Intensity | null;
  /** Remaining plan entries, for surfaces that offer "other options". */
  alternatives: RecommendedIntervention[];
  /** Why the policy landed where it did — for the pipeline console. */
  decisionReason: string | null;
  accept: () => void;
  dismiss: () => void;
}

const InterventionContext = createContext<InterventionContextValue | null>(null);

export function InterventionProvider({ children }: { children: ReactNode }) {
  const { rootCause } = useTracker();
  const location = useLocation();

  const [selected, setSelected] = useState<SelectedIntervention | null>(null);
  const [alternatives, setAlternatives] = useState<RecommendedIntervention[]>([]);
  const handledRunId = useRef<string | null>(null);

  // A navigation opens a fresh attention window and retires whatever was on
  // screen. The exposure stays `pending` — being navigated away from is exactly
  // the "ignored" signal that licenses escalating next time.
  useEffect(() => {
    fatigueBudget.noteRouteVisit(location.pathname);
    setSelected(null);
    setAlternatives([]);
  }, [location.pathname]);

  useEffect(() => {
    if (!rootCause) return;
    // One decision per pipeline run: the tracker re-renders on every poll, and
    // re-running the policy would burn budget on an analysis already spent.
    if (handledRunId.current === rootCause.pipeline_run_id) return;
    handledRunId.current = rootCause.pipeline_run_id;

    // The RCA gate never ran the diagnosis at all — "no intervention" is still
    // a decision, just one made a stage earlier than selectSurface. Only
    // gate_not_met is a business decision; rate_limited/not_configured/error
    // are operational failures, not a deliberate "do nothing" call.
    if (rootCause.status !== "success") {
      if (rootCause.status === "gate_not_met") {
        const probability = rootCause.prediction.abandonment_probability;
        const threshold = rootCause.gate.threshold;
        const summary =
          probability < threshold
            ? `user likely to convert unaided (p=${probability.toFixed(3)})`
            : rootCause.gate.reason;
        const decision: DeliveryDecision = {
          outcome: "held",
          reason: "gate_held",
          headline: `Decision: no intervention — ${summary}`,
          detail: rootCause.gate.reason,
          rootCause: null,
        };
        pipelineTrace.attachDecision(rootCause.pipeline_run_id, decision);
        interventionLedger.recordHeld({ reason: "gate_held", rootCause: null, detail: rootCause.gate.reason });
      }
      return;
    }

    const plan = rootCause.intervention_plan;
    const analysis = rootCause.analysis;
    if (!plan || !analysis) return;

    const ranked = [
      ...plan.top_interventions,
      ...(plan.fallback_intervention ? [plan.fallback_intervention] : []),
    ];

    const uncovered = assertPolicyCoverage(ranked.map((item) => item.lever_id));
    if (uncovered.length > 0 && import.meta.env.DEV) {
      console.warn(
        `[intervention] no delivery policy for lever(s): ${uncovered.join(", ")} — ` +
          "add them to LEVER_POLICY in src/lib/interventionPolicy.ts",
      );
    }

    const surfaceOptions: SelectSurfaceOptions = {
      rootCause: analysis.primary_root_cause.category,
      marginApproved: resolveMarginApproval(),
    };
    const outcome = selectSurface(ranked, analysis.confidence, fatigueBudget.getState(), surfaceOptions);

    // Every rung-3 lever the ranking considered but didn't deliver, regardless
    // of whether this run held entirely or delivered something else instead —
    // feeds the ledger's "promotional spend avoided" total.
    const deliveredLeverId = outcome.decision === "deliver" ? outcome.intervention.lever_id : null;
    const suppressedRung3 = findSuppressedRung3Levers(
      ranked,
      analysis.confidence,
      fatigueBudget.getState(),
      deliveredLeverId,
      surfaceOptions,
    );
    if (suppressedRung3.length > 0) interventionLedger.recordSuppressedRung3(suppressedRung3);

    if (outcome.decision === "hold") {
      // Deliberately leaves whatever is already on screen alone: it was paid
      // for, the shopper may be mid-read, and yanking it would spend the
      // exposure without delivering the message.
      pipelineTrace.attachDecision(rootCause.pipeline_run_id, {
        outcome: "held",
        reason: outcome.reason,
        headline: `Decision: no intervention — ${outcome.detail}`,
        detail: outcome.detail,
        rootCause: outcome.rootCause,
      });
      interventionLedger.recordHeld({
        reason: outcome.reason,
        rootCause: outcome.rootCause,
        detail: outcome.detail,
      });
      return;
    }

    const picked: SelectedIntervention = {
      intervention: outcome.intervention,
      surface: outcome.surface,
      intensity: outcome.intensity,
      rootCause: outcome.rootCause,
      reason: outcome.reason,
    };

    // `inline`/`spotlight` attach to a specific on-page element. If that
    // element isn't mounted right now (e.g. the lever's page isn't the one
    // the shopper is on), fall back one rung to the ambient card rather than
    // dropping the intervention silently.
    const targetKeys = LEVER_TARGET_KEYS[picked.intervention.lever_id] ?? [];
    const delivered: SelectedIntervention =
      (picked.surface === "inline" || picked.surface === "spotlight") && !getAllMounted(targetKeys)
        ? { ...picked, surface: "ambient", intensity: 1 }
        : picked;

    fatigueBudget.recordShown(delivered.intervention.lever_id, {
      rootCause: delivered.rootCause,
      intensity: delivered.intensity,
    });
    pipelineTrace.attachDecision(rootCause.pipeline_run_id, {
      outcome: "delivered",
      headline: `Decision: deliver ${delivered.intervention.lever_id} at rung ${delivered.intensity} (${delivered.surface})`,
      detail: delivered.reason,
      rootCause: delivered.rootCause,
      leverId: delivered.intervention.lever_id,
      intensity: delivered.intensity,
      surface: delivered.surface,
    });
    setSelected(delivered);
    setAlternatives(ranked.filter((item) => item.lever_id !== delivered.intervention.lever_id));
  }, [rootCause]);

  const resolve = useCallback(
    (action: "accepted" | "dismissed") => {
      const leverId = selected?.intervention.lever_id;
      if (!leverId) return;
      // Single feedback path — `sendInterventionFeedback` in lib/tracker.ts is
      // the only writer to /api/intervention-feedback.
      void sendInterventionFeedback(leverId, action);
      if (action === "accepted") fatigueBudget.recordAccepted(leverId);
      else fatigueBudget.recordDismissed(leverId);
      setSelected(null);
      setAlternatives([]);
    },
    [selected],
  );

  const value = useMemo<InterventionContextValue>(
    () => ({
      active: selected?.intervention ?? null,
      surface: selected?.surface ?? null,
      intensity: selected?.intensity ?? null,
      alternatives,
      decisionReason: selected?.reason ?? null,
      accept: () => resolve("accepted"),
      dismiss: () => resolve("dismissed"),
    }),
    [selected, alternatives, resolve],
  );

  return <InterventionContext.Provider value={value}>{children}</InterventionContext.Provider>;
}

export function useIntervention(): InterventionContextValue {
  const context = useContext(InterventionContext);
  if (!context) throw new Error("useIntervention must be used within InterventionProvider");
  return context;
}
