/**
 * Attention budget for proactive interventions.
 *
 * The backend already penalises repeats when it *scores* levers
 * (`agents/intervention.py`'s repetition_penalty). This is the other half: the
 * client decides whether the moment is worth spending at all. Ranking answers
 * "which one", this answers "should we interrupt right now".
 *
 * Two ideas do the work:
 *
 * 1. **Exposure decays.** The session cap is applied to a decayed sum, not a raw
 *    counter. Each exposure starts at 1.0 and halves every `HALF_LIFE_MS`, so a
 *    shopper who was shown three things and then browsed quietly for ten minutes
 *    earns budget back. A hard counter would lock a long session out permanently,
 *    which is the wrong failure mode for a 45-minute research session.
 *
 * 2. **Dismissal is heavier than being ignored.** Ignoring is ambiguous — the
 *    shopper may simply not have looked. Dismissing is an explicit "no", so that
 *    lever is suppressed for the rest of the session and no amount of decay
 *    brings it back. Being ignored, by contrast, is what licenses escalation in
 *    `interventionPolicy.ts`.
 *
 * State lives in sessionStorage so a reload mid-demo doesn't hand the shopper a
 * fresh budget, matching how `tracker.ts` scopes its session id.
 */

export type ExposureOutcome = "pending" | "accepted" | "dismissed";

export interface Exposure {
  leverId: string;
  /** Diagnosed root-cause category this exposure was spent on. */
  rootCause: string;
  intensity: number;
  shownAt: number;
  outcome: ExposureOutcome;
}

export interface FatigueState {
  exposures: Exposure[];
  /** Explicit "no" list — terminal for the session, immune to decay. */
  dismissedLeverIds: string[];
  lastShownAt: number;
  /** Identifies the current route *visit*, not the route. */
  routeVisitId: string;
  shownInCurrentVisit: boolean;
  hasElicited: boolean;
}

export type BlockReason = "session_cap" | "cooldown" | "route_cap" | "dismissed_type";

export type ShowVerdict =
  | { allowed: true }
  | { allowed: false; reason: BlockReason };

export interface FatigueSnapshot {
  /** Raw count, for the operator-facing readout. */
  exposureCount: number;
  /** Decayed sum — the number the session cap is actually applied to. */
  decayedExposure: number;
  remainingBudget: number;
  /** Epoch ms when the cooldown lifts; null when nothing has been shown. */
  nextEligibleAt: number | null;
  dismissedLeverIds: string[];
  shownInCurrentVisit: boolean;
  hasElicited: boolean;
  exposures: Exposure[];
}

const STORAGE_KEY = "fk-intervention-fatigue-v1";

/** Hard caps, tuned for live demo responsiveness. */
export const MAX_SESSION_EXPOSURE = 20;
export const MIN_GAP_MS = 3_000;

/**
 * 2 minutes decay half-life for demo.
 */
export const HALF_LIFE_MS = 120_000;

const EMPTY_STATE: FatigueState = {
  exposures: [],
  dismissedLeverIds: [],
  lastShownAt: 0,
  routeVisitId: "",
  shownInCurrentVisit: false,
  hasElicited: false,
};

function newVisitId(pathname: string): string {
  return `${pathname}#${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

class FatigueBudget {
  private state: FatigueState = this.load();
  private listeners = new Set<() => void>();
  /** Cached immutable snapshot so useSyncExternalStore doesn't loop. */
  private snapshot: FatigueSnapshot = this.buildSnapshot();

  private load(): FatigueState {
    if (typeof window === "undefined") return { ...EMPTY_STATE };
    try {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return { ...EMPTY_STATE };
      const parsed = JSON.parse(raw) as Partial<FatigueState>;
      return {
        ...EMPTY_STATE,
        ...parsed,
        exposures: parsed.exposures ?? [],
        dismissedLeverIds: parsed.dismissedLeverIds ?? [],
        hasElicited: parsed.hasElicited ?? false,
      };
    } catch {
      // Corrupt or unavailable storage should never break shopping.
      return { ...EMPTY_STATE };
    }
  }

  private persist(): void {
    if (typeof window === "undefined") return;
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
    } catch {
      // Quota or private-mode failures degrade to in-memory tracking.
    }
  }

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getSnapshot = (): FatigueSnapshot => this.snapshot;

  private commit(): void {
    this.persist();
    this.snapshot = this.buildSnapshot();
    this.listeners.forEach((listener) => listener());
  }

  /** Read-only view for the policy layer. */
  getState(): FatigueState {
    return this.state;
  }

  /** Exposure weight halves every HALF_LIFE_MS. */
  private decayedExposure(now: number): number {
    return this.state.exposures.reduce(
      (total, exposure) =>
        total + 0.5 ** (Math.max(0, now - exposure.shownAt) / HALF_LIFE_MS),
      0,
    );
  }

  private buildSnapshot(now = Date.now()): FatigueSnapshot {
    const decayed = this.decayedExposure(now);
    return {
      exposureCount: this.state.exposures.length,
      decayedExposure: Number(decayed.toFixed(2)),
      remainingBudget: Number(Math.max(0, MAX_SESSION_EXPOSURE - decayed).toFixed(2)),
      nextEligibleAt: this.state.lastShownAt > 0 ? this.state.lastShownAt + MIN_GAP_MS : null,
      dismissedLeverIds: [...this.state.dismissedLeverIds],
      shownInCurrentVisit: this.state.shownInCurrentVisit,
      hasElicited: this.state.hasElicited,
      exposures: [...this.state.exposures],
    };
  }

  hasElicitedThisSession(): boolean {
    return this.state.hasElicited;
  }

  recordElicited(now = Date.now()): void {
    this.state.hasElicited = true;
    this.recordShown("elicitation_prompt", { rootCause: "unknown", intensity: 1 }, now);
  }

  /**
   * Ordered cheapest-check-last so the caller can tell a per-candidate block
   * (`dismissed_type` — try the next lever) from a session-level one (stop).
   */
  canShow(intervention: { lever_id: string }, now = Date.now()): ShowVerdict {
    if (this.state.dismissedLeverIds.includes(intervention.lever_id)) {
      return { allowed: false, reason: "dismissed_type" };
    }
    // The exposure about to be spent has to fit inside the budget. Testing the
    // running total alone would let a 4th through on a burst, because three
    // near-simultaneous exposures decay to just under 3 before the check runs.
    if (this.decayedExposure(now) + 1 > MAX_SESSION_EXPOSURE + 1e-9) {
      return { allowed: false, reason: "session_cap" };
    }
    if (this.state.lastShownAt > 0 && now - this.state.lastShownAt < MIN_GAP_MS) {
      return { allowed: false, reason: "cooldown" };
    }
    return { allowed: true };
  }

  recordShown(
    leverId: string,
    meta: { rootCause: string; intensity: number },
    now = Date.now(),
  ): void {
    this.state.exposures = [
      ...this.state.exposures,
      {
        leverId,
        rootCause: meta.rootCause,
        intensity: meta.intensity,
        shownAt: now,
        outcome: "pending",
      },
    ];
    this.state.lastShownAt = now;
    this.state.shownInCurrentVisit = true;
    this.commit();
  }

  /**
   * Terminal for the session. Resolves the most recent pending exposure of this
   * lever so it stops counting as "ignored" for escalation purposes.
   */
  recordDismissed(leverId: string): void {
    this.resolveLatest(leverId, "dismissed");
    if (!this.state.dismissedLeverIds.includes(leverId)) {
      this.state.dismissedLeverIds = [...this.state.dismissedLeverIds, leverId];
    }
    this.commit();
  }

  recordAccepted(leverId: string): void {
    this.resolveLatest(leverId, "accepted");
    this.commit();
  }

  private resolveLatest(leverId: string, outcome: ExposureOutcome): void {
    const index = this.state.exposures.findLastIndex(
      (exposure) => exposure.leverId === leverId && exposure.outcome === "pending",
    );
    if (index === -1) return;
    const updated = [...this.state.exposures];
    updated[index] = { ...updated[index], outcome };
    this.state.exposures = updated;
  }

  /**
   * A navigation opens a new attention window. Re-entering the same path counts
   * as a fresh visit — the shopper left and came back, which is a new moment.
   */
  noteRouteVisit(pathname: string): void {
    const visitId = newVisitId(pathname);
    if (this.state.routeVisitId === visitId) return;
    this.state.routeVisitId = visitId;
    this.state.shownInCurrentVisit = false;
    this.commit();
  }

  /** Demo control — lets a scenario be re-run without waiting out the cooldown. */
  reset(): void {
    this.state = { ...EMPTY_STATE };
    this.commit();
  }

  /**
   * Demo control — backdates `count` synthetic "pending" (i.e. ignored)
   * exposures for `rootCause`, so a scenario's very first real analysis
   * already computes an escalated target rung instead of needing 2-3 manual
   * re-runs to accumulate real ignored history. Backdated well past
   * `MIN_GAP_MS` so it doesn't trip the cooldown on the run that follows.
   */
  seedIgnored(rootCause: string, count: number, now = Date.now()): void {
    for (let i = 0; i < count; i += 1) {
      this.state.exposures = [
        ...this.state.exposures,
        {
          leverId: "_seed_escalation",
          rootCause,
          intensity: 1,
          shownAt: now - MIN_GAP_MS - 5_000 - i * 100,
          outcome: "pending",
        },
      ];
    }
    this.commit();
  }
}

export const fatigueBudget = new FatigueBudget();
