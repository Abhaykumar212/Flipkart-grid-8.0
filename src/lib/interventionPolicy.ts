/**
 * Delivery policy — how loudly an intervention is allowed to speak.
 *
 * The backend ranks levers by *expected value* (`agents/intervention.py`). It has
 * no view on how much of the shopper's attention each one costs to deliver, and
 * a correct recommendation delivered as a modal can be worse than no
 * recommendation at all. This module supplies the missing axis.
 *
 * The intensity ladder, lowest to highest:
 *
 *   0  passive  — inline, borrows no attention; the shopper may never notice it
 *   1  ambient  — edge-docked and dismissible; noticed, easy to ignore
 *   2  active   — spotlight/modal; takes the foreground, must be earned
 *   3  costly   — anything with margin impact (waived fees, discount codes)
 *
 * Rung 3 is not a louder rung 2. It is the rung that spends money, so it is
 * gated on an explicit operator approval as well as high diagnostic confidence:
 * an uncertain diagnosis must never be able to discount its way out of doubt.
 *
 * Lever ids are the closed set from `backend/agents/levers.py`. Nothing here
 * invents one, and `assertPolicyCoverage` fails loudly if the catalog grows
 * without a matching entry.
 */

import { fatigueBudget, type FatigueState } from "./fatigueBudget";
import type { NoInterventionReason, RecommendedIntervention } from "./pipelineTrace";

export type InterventionSurface = "inline" | "ambient" | "spotlight" | "companion";

/** 0 passive · 1 ambient · 2 active · 3 costly. */
export type Intensity = 0 | 1 | 2 | 3;

export type DiagnosisConfidence = "high" | "medium" | "low";

export interface LeverPolicy {
  intensity: Intensity;
  surface: InterventionSurface;
}

/**
 * One entry per lever in `LEVER_CATALOG`.
 *
 * `intensity` is the cost/escalation rung (unchanged from the original design —
 * rung 3 is still gated on margin approval, see `selectSurface` below). `surface`
 * is which on-page primitive renders it, keyed to where each lever's content
 * actually makes sense on the page: delivery-reassurance and price levers land
 * inline on the delivery line / `PriceBlock` / EMI row they're talking about;
 * review-summary lands inline on the reviews header; the one lever closest to
 * "show me alternatives" (`stock_scarcity_nudge`) spotlights the similar-products
 * rail; reassurance/save-for-later levers with no natural page anchor go to the
 * ambient card; anything conversation-shaped hands off to `CompanionWidget`.
 */
export const LEVER_POLICY: Record<string, LeverPolicy> = {
  // Rung 0 — passive. Content the page could plausibly have shown anyway.
  trust_badge_reassurance: { intensity: 0, surface: "ambient" },
  stock_scarcity_nudge: { intensity: 0, surface: "spotlight" },
  emi_plan_highlight: { intensity: 0, surface: "inline" },
  // Off-session action; the only on-page cost is a line confirming it will happen.
  abandoned_cart_email: { intensity: 0, surface: "ambient" },

  // Rung 1 — ambient. Noticed, dismissible, no foreground claim.
  price_drop_alert: { intensity: 1, surface: "inline" },
  saved_payment_prompt: { intensity: 1, surface: "ambient" },
  guest_to_account_nudge: { intensity: 1, surface: "ambient" },
  review_summary_surface: { intensity: 1, surface: "inline" },

  // Rung 2 — active. Interruptive by design, so it has to be earned.
  exit_intent_reminder: { intensity: 2, surface: "ambient" },
  payment_retry_help: { intensity: 2, surface: "companion" },
  checkout_assist_chat: { intensity: 2, surface: "companion" },

  // Rung 3 — costly. Every one of these gives away margin.
  free_delivery_waiver: { intensity: 3, surface: "inline" },
  delivery_speed_upgrade: { intensity: 3, surface: "inline" },
  targeted_discount_code: { intensity: 3, surface: "inline" },
};

/**
 * Confidence gates the rung the ladder starts on and how high it may climb.
 * A low-confidence diagnosis is never allowed into the foreground: the worst
 * outcome is interrupting a shopper over a barrier that was never there. A
 * confident one is allowed to open at ambient rather than whisper inline, but
 * still has to earn anything above that.
 */
const CONFIDENCE_BAND: Record<DiagnosisConfidence, { start: Intensity; ceiling: Intensity }> = {
  low: { start: 0, ceiling: 1 },
  medium: { start: 0, ceiling: 2 },
  high: { start: 1, ceiling: 3 },
};

const MARGIN_APPROVAL_KEY = "fk-intervention-margin-approval";

/** Operator approval for margin-spending levers. Defaults to withheld. */
export function resolveMarginApproval(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(MARGIN_APPROVAL_KEY) === "true";
  } catch {
    return false;
  }
}

export function setMarginApproval(approved: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(MARGIN_APPROVAL_KEY, approved ? "true" : "false");
  } catch {
    // Non-fatal: the gate simply stays at its default of withheld.
  }
}

export interface SelectedIntervention {
  intervention: RecommendedIntervention;
  surface: InterventionSurface;
  intensity: Intensity;
  rootCause: string;
  /** Why this rung — surfaced in the console so the choice is inspectable. */
  reason: string;
}

export const ELICITATION_PROBABILITY_THRESHOLD = 0.0;

export interface SelectSurfaceOptions {
  marginApproved?: boolean;
  /** Diagnosed primary root-cause category; escalation is tracked per cause. */
  rootCause?: string;
  now?: number;
  probability?: number;
  hasElicited?: boolean;
}

/**
 * `selectSurface` never returns bare `null`: "nothing rendered" is a decision
 * with a reason, not an absence, so it always comes back as one arm of this
 * union. `no_lever_above_threshold` is the catch-all — every candidate was
 * either off-policy or previously dismissed, without one of the more specific
 * reasons below applying.
 */
export type SurfaceDecision =
  | ({ decision: "deliver" } & SelectedIntervention)
  | { decision: "hold"; reason: NoInterventionReason; detail: string; rootCause: string }
  | { decision: "elicit"; reason: string; detail: string; rootCause: string };

export type Rung3SuppressionReason =
  | "confidence_gate"
  | "margin_approval_required"
  | "escalation_pending"
  | "fatigue";

export interface SuppressedRung3Lever {
  leverId: string;
  reason: Rung3SuppressionReason;
}

/**
 * Nominal assumed discount value per rung-3 lever, INR. Hackathon assumption —
 * same caveat `levers.py` already applies to `expected_conversion_gain` — used
 * only to make the "promotional spend avoided" arithmetic visible in the
 * ledger UI, not a measured cost.
 */
export const RUNG3_ASSUMED_VALUE_INR: Record<string, number> = {
  targeted_discount_code: 200,
  free_delivery_waiver: 40,
  delivery_speed_upgrade: 60,
};

/**
 * How many interventions for this root cause were shown and left unanswered.
 *
 * Only `pending` counts. An accepted intervention worked, and a dismissed one is
 * an explicit no — neither is grounds for coming back louder. Escalation is
 * earned by being *ignored*, which is the one outcome that says "the shopper
 * never engaged with this".
 *
 * Counting attempts rather than tracking the highest rung reached matters:
 * a category may have no lever at all at some rung, and keying off the rung
 * would leave the ladder stuck below the gap forever.
 */
function ignoredCount(state: FatigueState, rootCause: string): number {
  return state.exposures.filter(
    (exposure) => exposure.rootCause === rootCause && exposure.outcome === "pending",
  ).length;
}

interface CeilingInfo {
  band: { start: Intensity; ceiling: Intensity };
  marginAllowed: boolean;
  /** True when confidence alone would allow rung 3 but approval withheld it. */
  marginClamped: boolean;
  ceiling: Intensity;
  ignored: number;
  target: Intensity;
}

/** Shared by `selectSurface` and `findSuppressedRung3Levers` so the two never disagree. */
function computeCeiling(
  confidence: DiagnosisConfidence,
  fatigueState: FatigueState,
  rootCause: string,
  marginApproved: boolean,
): CeilingInfo {
  const band = CONFIDENCE_BAND[confidence] ?? CONFIDENCE_BAND.low;

  // Rung 3 spends money, so it needs both a confident diagnosis and a human's
  // standing approval. Without either, the ladder tops out one rung lower.
  const marginAllowed = confidence === "high" && marginApproved;
  const marginClamped = band.ceiling === 3 && !marginAllowed;
  const ceiling: Intensity = marginClamped ? 2 : band.ceiling;

  // One rung per ignored attempt on this cause, never past the ceiling.
  const ignored = ignoredCount(fatigueState, rootCause);
  const target = Math.min(ceiling, band.start + ignored) as Intensity;

  return { band, marginAllowed, marginClamped, ceiling, ignored, target };
}

/**
 * Picks at most ONE intervention to render, or explains why nothing qualified.
 *
 * `ranked` arrives in backend score order; within a rung that order is respected
 * untouched. This function never reorders on value, only filters on cost.
 */
export function selectSurface(
  ranked: RecommendedIntervention[],
  confidence: DiagnosisConfidence,
  fatigueState: FatigueState,
  options: SelectSurfaceOptions = {},
): SurfaceDecision {
  const rootCause = options.rootCause ?? "unknown";
  const marginApproved = options.marginApproved ?? resolveMarginApproval();
  const now = options.now ?? Date.now();

  const { band, marginClamped, ceiling, ignored, target } = computeCeiling(
    confidence,
    fatigueState,
    rootCause,
    marginApproved,
  );

  const reason =
    ignored === 0
      ? `${confidence} confidence → start at rung ${band.start} (ceiling ${ceiling})`
      : `${ignored} ignored on ${rootCause} → escalate to rung ${target} (ceiling ${ceiling})`;

  if (ranked.length === 0) {
    return {
      decision: "hold",
      reason: "no_lever_above_threshold",
      detail: "no candidate lever survived ranking for this diagnosis",
      rootCause,
    };
  }

  // Walk down from the target: never louder than earned, but a quieter lever is
  // always an acceptable substitute for one that isn't available.
  for (let rung = target; rung >= 0; rung -= 1) {
    for (const intervention of ranked) {
      const policy = LEVER_POLICY[intervention.lever_id];
      if (!policy || policy.intensity !== rung) continue;

      const verdict = fatigueBudget.canShow(intervention, now);
      if (verdict.allowed) {
        return {
          decision: "deliver",
          intervention,
          surface: policy.surface,
          intensity: policy.intensity,
          rootCause,
          reason,
        };
      }
      // A per-candidate block just disqualifies that lever; a session-level cap
      // is the whole budget saying no, and looking harder won't change it.
      if (verdict.reason === "session_cap") {
        return {
          decision: "hold",
          reason: "fatigue_cap",
          detail: "session attention budget is spent for this session (decayed exposure at cap)",
          rootCause,
        };
      }
      if (verdict.reason === "cooldown") {
        return {
          decision: "hold",
          reason: "cooldown",
          detail: "the minimum gap since the last intervention hasn't elapsed yet",
          rootCause,
        };
      }
      if (verdict.reason === "route_cap") {
        return {
          decision: "hold",
          reason: "fatigue_cap",
          detail: "an intervention was already shown on this page visit",
          rootCause,
        };
      }
      // dismissed_type: this lever is off the table for the session; try the next candidate.
    }
  }

  // Walked every rung down to 0 with no eligible candidate.
  if (marginClamped && ranked.some((item) => LEVER_POLICY[item.lever_id]?.intensity === 3)) {
    return {
      decision: "hold",
      reason: "margin_approval_required",
      detail: "the top lever spends margin (rung 3) but no operator approval is on file",
      rootCause,
    };
  }
  if (confidence === "low") {
    if (
      options.probability !== undefined &&
      options.probability >= ELICITATION_PROBABILITY_THRESHOLD &&
      !options.hasElicited
    ) {
      return {
        decision: "elicit",
        reason: "low_confidence_hesitation",
        detail: `probability (${options.probability.toFixed(3)}) >= ${ELICITATION_PROBABILITY_THRESHOLD} with low diagnostic confidence`,
        rootCause,
      };
    }
    return {
      decision: "hold",
      reason: "low_confidence",
      detail: "diagnosis confidence is too low to justify surfacing any lever",
      rootCause,
    };
  }
  return {
    decision: "hold",
    reason: "no_lever_above_threshold",
    detail: "no lever cleared the policy threshold for this session",
    rootCause,
  };
}

/**
 * Every rung-3 (costly) lever present in the ranked plan that did NOT get
 * delivered this run, with why — feeds the "promotional spend avoided" ledger.
 * Computed independently of `selectSurface`'s single winning pick: more than
 * one rung-3 candidate can be suppressed in the same run, and one can be
 * suppressed even in a run that delivered something else at a lower rung.
 */
export function findSuppressedRung3Levers(
  ranked: RecommendedIntervention[],
  confidence: DiagnosisConfidence,
  fatigueState: FatigueState,
  deliveredLeverId: string | null,
  options: SelectSurfaceOptions = {},
): SuppressedRung3Lever[] {
  const rootCause = options.rootCause ?? "unknown";
  const marginApproved = options.marginApproved ?? resolveMarginApproval();
  const { band, marginClamped, target } = computeCeiling(confidence, fatigueState, rootCause, marginApproved);

  const reason: Rung3SuppressionReason =
    band.ceiling < 3
      ? "confidence_gate"
      : marginClamped
        ? "margin_approval_required"
        : target < 3
          ? "escalation_pending"
          : "fatigue";

  return ranked
    .filter((item) => LEVER_POLICY[item.lever_id]?.intensity === 3 && item.lever_id !== deliveredLeverId)
    .map((item) => ({ leverId: item.lever_id, reason }));
}

/**
 * Catalog-parity guard. A lever added to `levers.py` without a policy entry here
 * would silently never render; this makes that a visible error in dev instead.
 */
export function assertPolicyCoverage(leverIds: string[]): string[] {
  return leverIds.filter((leverId) => !(leverId in LEVER_POLICY));
}
