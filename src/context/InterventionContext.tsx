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
import { sendDeliveryDecision, sendElicitationResponse, sendInterventionFeedback, SESSION_ID } from "../lib/tracker";
import { fatigueBudget } from "../lib/fatigueBudget";
import * as abTesting from "../lib/abTesting";
import {
  assertPolicyCoverage,
  findSuppressedRung3Levers,
  LEVER_POLICY,
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
import { pageContext } from "../lib/pageContext";
import type { RootCauseAnalysis } from "../lib/pipelineTrace";
import { useCart } from "./CartContext";
import { computeCartTotals } from "../lib/cartTotals";
import { productById } from "../data/products";
import { buildOutcome, type InterventionOutcome } from "../lib/interventionOutcomes";

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
  /**
   * Diagnosis bound to the product being analysed. Passive content adaptation
   * reads this even when delivery deliberately chose do_nothing; it is not an
   * intervention and never consumes the intensity/fatigue budget.
   */
  diagnosis: { productId: string; analysis: RootCauseAnalysis } | null;
  isEliciting: boolean;
  submitElicitationResponse: (chip: "Price" | "Trust or quality" | "Still comparing") => Promise<void>;
  dismissElicitation: () => void;
  accept: () => void;
  dismiss: () => void;
  /** The concrete result of the most recently accepted intervention — a discount, a delivery perk, etc. */
  ctaOutcome: InterventionOutcome | null;
  dismissOutcome: () => void;
}

const InterventionContext = createContext<InterventionContextValue | null>(null);

export function InterventionProvider({ children }: { children: ReactNode }) {
  const { rootCause, runRootCauseAnalysis } = useTracker();
  const { items, applyPromo, unlockFreeDelivery, unlockExpressDelivery } = useCart();
  const location = useLocation();

  const [selected, setSelected] = useState<SelectedIntervention | null>(null);
  const [alternatives, setAlternatives] = useState<RecommendedIntervention[]>([]);
  const [diagnosis, setDiagnosis] = useState<InterventionContextValue["diagnosis"]>(null);
  const [isEliciting, setIsEliciting] = useState(false);
  const [ctaOutcome, setCtaOutcome] = useState<InterventionOutcome | null>(null);
  const handledRunId = useRef<string | null>(null);
  // Mutable, not state: read once by the next analysis run and cleared there,
  // not something that should itself trigger a re-render or an effect re-run.
  const exitIntentRef = useRef(false);
  // Separate one-shot guard so a mouse that leaves the viewport repeatedly
  // doesn't force a fresh (paid) LLM call every time — once per cart visit.
  const exitIntentFiredRef = useRef(false);

  // A/B testing framework: resolve this session's arm once, early — reads
  // are synchronous after (`abTesting.getVariant()`), the fetch just needs to
  // land before the first `runRootCauseAnalysis` result arrives.
  useEffect(() => {
    void abTesting.ensureLoaded(SESSION_ID);
  }, []);

  // A navigation opens a fresh attention window and retires whatever was on
  // screen. The exposure stays `pending` — being navigated away from is exactly
  // the "ignored" signal that licenses escalating next time.
  useEffect(() => {
    fatigueBudget.noteRouteVisit(location.pathname);
    setSelected(null);
    setAlternatives([]);
    setCtaOutcome(null);
    exitIntentRef.current = false;
    exitIntentFiredRef.current = false;
  }, [location.pathname]);

  // Real exit intent, cart page only: the mouse crossing the top edge toward
  // the tab/address bar is the standard "about to leave" signal. Gated to
  // /cart specifically — margin should only be spent as a last resort on the
  // page where leaving means abandoning the purchase outright. Forces an
  // immediate re-analysis rather than waiting for the next 5s poll, so the
  // override is demoable ("mouse leaves → discount appears"), not timing-luck.
  useEffect(() => {
    if (location.pathname !== "/cart") return;
    const handleMouseLeave = (event: MouseEvent) => {
      if (event.clientY > 0 || exitIntentFiredRef.current) return;
      exitIntentFiredRef.current = true;
      exitIntentRef.current = true;
      void runRootCauseAnalysis({ force: true });
    };
    document.addEventListener("mouseleave", handleMouseLeave);
    return () => document.removeEventListener("mouseleave", handleMouseLeave);
  }, [location.pathname, runRootCauseAnalysis]);

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
    const analysis = rootCause.analysis;
    if (analysis) {
      // Passive diagnosis consumers are updated independently of delivery.
      // This includes critic-blocked/do_nothing outcomes and spends no budget.
      const productId = pageContext.getSnapshot().currentProductId ?? items[0]?.productId;
      setDiagnosis(productId ? { productId, analysis } : null);
    } else {
      setDiagnosis(null);
    }

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
        void sendDeliveryDecision({
          outcome: "held",
          reason: "gate_held",
          detail: rootCause.gate.reason,
          root_cause: null,
          probability,
        });
      }
      return;
    }

    const plan = rootCause.intervention_plan;
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

    // Consumed once: the next run after a genuine exit-intent event gets the
    // override, then it's spent regardless of what that run decided.
    const exitIntent = exitIntentRef.current;
    exitIntentRef.current = false;

    const surfaceOptions: SelectSurfaceOptions = {
      rootCause: analysis.primary_root_cause.category,
      marginApproved: resolveMarginApproval(),
      probability: rootCause.prediction.abandonment_probability,
      hasElicited: fatigueBudget.hasElicitedThisSession(),
      exitIntent,
      abVariant: abTesting.getVariant(),
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

    // Reported on the same POST as the decision itself — a suppressed lever that
    // landed without its decision (or vice versa) would skew the ledger's
    // spend-avoided total against a run that never happened.
    const suppressedForServer = suppressedRung3.map((item) => ({
      lever_id: item.leverId,
      reason: item.reason,
    }));
    const probability = rootCause.prediction.abandonment_probability;

    if (outcome.decision === "elicit") {
      fatigueBudget.recordElicited();
      pipelineTrace.attachDecision(rootCause.pipeline_run_id, {
        outcome: "delivered",
        headline: "Decision: elicit shopper intent (Rung 1, Companion)",
        detail: outcome.detail,
        rootCause: outcome.rootCause,
      });
      void sendDeliveryDecision({
        outcome: "elicited",
        reason: outcome.reason,
        detail: outcome.detail,
        root_cause: outcome.rootCause,
        probability,
        confidence: analysis.confidence,
        suppressed: suppressedForServer,
      });
      setIsEliciting(true);
      return;
    }

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
      void sendDeliveryDecision({
        outcome: "held",
        reason: outcome.reason,
        detail: outcome.detail,
        root_cause: outcome.rootCause,
        probability,
        confidence: analysis.confidence,
        suppressed: suppressedForServer,
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
    void sendDeliveryDecision({
      outcome: "delivered",
      reason: delivered.reason,
      detail: delivered.reason,
      root_cause: delivered.rootCause,
      probability,
      lever_id: delivered.intervention.lever_id,
      intensity_rung: delivered.intensity,
      surface: delivered.surface,
      confidence: analysis.confidence,
      suppressed: suppressedForServer,
    });
    setSelected(delivered);
    setAlternatives(ranked.filter((item) => item.lever_id !== delivered.intervention.lever_id));
  }, [rootCause, items]);

  const resolve = useCallback(
    (action: "accepted" | "dismissed") => {
      const leverId = selected?.intervention.lever_id;
      if (!leverId || !selected) return;

      if (action === "accepted") {
        fatigueBudget.recordAccepted(leverId);
        // Actionable DOM navigation & modal triggers
        if (leverId === "emi_plan_highlight") {
          const emiEl = document.getElementById("emi-options") || document.querySelector("[data-section='emi']");
          if (emiEl) emiEl.scrollIntoView({ behavior: "smooth" });
        } else if (leverId === "review_summary_surface") {
          const reviewsEl = document.getElementById("customer-reviews") || document.querySelector("[data-section='reviews']");
          if (reviewsEl) reviewsEl.scrollIntoView({ behavior: "smooth" });
        } else if (leverId === "stock_scarcity_nudge") {
          const similarEl = document.getElementById("similar-products") || document.querySelector("[data-section='similar']");
          if (similarEl) similarEl.scrollIntoView({ behavior: "smooth" });
        } else if (leverId === "delivery_speed_upgrade" || leverId === "free_delivery_waiver") {
          const deliveryEl = document.getElementById("delivery-pincode");
          if (deliveryEl) {
            deliveryEl.scrollIntoView({ behavior: "smooth" });
            const input = deliveryEl.querySelector("input");
            if (input) input.focus();
          }
        }

        // Concrete, visible consequence — a discount actually applied, a
        // delivery perk actually unlocked — not just the card disappearing.
        const totals = computeCartTotals(items);
        const slowestDeliveryDays = items.reduce((max, item) => {
          const product = productById.get(item.productId);
          return product ? Math.max(max, product.delivery.estimatedDays) : max;
        }, 0);
        const built = buildOutcome(leverId, {
          cartValue: totals.totalSellingPrice,
          slowestDeliveryDays,
        });
        if (built) {
          if (built.promo) {
            applyPromo({ code: built.promo.code, amountOff: built.promo.amountOff, label: built.title, leverId });
          } else if (built.kind === "free_delivery") {
            unlockFreeDelivery();
          } else if (built.kind === "express_delivery") {
            unlockExpressDelivery();
          }
          setCtaOutcome(built);
        }
      } else {
        fatigueBudget.recordDismissed(leverId);
      }

      void sendInterventionFeedback(leverId, action, {
        intensity_rung: selected.intensity,
        surface: selected.surface,
        root_cause: selected.rootCause,
        confidence: selected.intervention.confidence,
      });
      setSelected(null);
      setAlternatives([]);
    },
    [selected, items, applyPromo, unlockFreeDelivery, unlockExpressDelivery],
  );

  const submitElicitationResponse = useCallback(
    async (chip: "Price" | "Trust or quality" | "Still comparing") => {
      setIsEliciting(false);
      const probability = rootCause?.prediction?.abandonment_probability;
      const res = await sendElicitationResponse(chip, probability);
      if (res && res.status === "success" && res.intervention_plan) {
        const plan = res.intervention_plan;
        const top = plan.top_interventions[0];
        if (top) {
          const policy = LEVER_POLICY[top.lever_id];
          const picked: SelectedIntervention = {
            intervention: top,
            surface: policy?.surface ?? "companion",
            intensity: policy?.intensity ?? 1,
            rootCause: res.analysis?.primary_root_cause?.category ?? "cost_friction",
            reason: `User-elicited (${chip})`,
          };
          fatigueBudget.recordShown(top.lever_id, {
            rootCause: picked.rootCause,
            intensity: picked.intensity,
          });
          setSelected(picked);
          setAlternatives(plan.top_interventions.slice(1));
        }
      }
    },
    [rootCause],
  );

  const dismissElicitation = useCallback(() => {
    setIsEliciting(false);
  }, []);

  const dismissOutcome = useCallback(() => setCtaOutcome(null), []);

  const value = useMemo<InterventionContextValue>(
    () => ({
      active: selected?.intervention ?? null,
      surface: selected?.surface ?? null,
      intensity: selected?.intensity ?? null,
      alternatives,
      decisionReason: selected?.reason ?? null,
      diagnosis,
      isEliciting,
      submitElicitationResponse,
      dismissElicitation,
      accept: () => resolve("accepted"),
      dismiss: () => resolve("dismissed"),
      ctaOutcome,
      dismissOutcome,
    }),
    [
      selected,
      alternatives,
      diagnosis,
      isEliciting,
      submitElicitationResponse,
      dismissElicitation,
      resolve,
      ctaOutcome,
      dismissOutcome,
    ],
  );

  return <InterventionContext.Provider value={value}>{children}</InterventionContext.Provider>;
}

export function useIntervention(): InterventionContextValue {
  const context = useContext(InterventionContext);
  if (!context) throw new Error("useIntervention must be used within InterventionProvider");
  return context;
}
