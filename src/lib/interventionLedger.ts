/**
 * Session-scoped ledger of delivery-layer decisions, across every pipeline run.
 *
 * `fatigueBudget` already tracks *what was shown* (exposures, rung, outcome) —
 * this is its complement: what was deliberately withheld, why, and which
 * rung-3 (costly) levers were considered and then suppressed by policy. Backs
 * the ledger panel on `/pipeline`. Nothing here re-derives shown/accepted/
 * dismissed counts — those read straight off `fatigueBudget`'s exposures,
 * which stays the single source of truth for what actually rendered.
 *
 * State lives in sessionStorage, matching `fatigueBudget.ts` and `tracker.ts`'s
 * session id — a reload mid-demo shouldn't zero out the ledger judges are
 * reading.
 */

import type { NoInterventionReason } from "./pipelineTrace";
import { RUNG3_ASSUMED_VALUE_INR } from "./interventionPolicy";

export interface HeldDecisionRecord {
  reason: NoInterventionReason;
  rootCause: string | null;
  detail: string;
  at: number;
}

export interface SuppressedLeverRecord {
  leverId: string;
  reason: string;
  at: number;
}

export interface SpendAvoidedEntry {
  count: number;
  assumedUnitValueInr: number;
  totalInr: number;
}

export interface LedgerSnapshot {
  held: HeldDecisionRecord[];
  heldByReason: Partial<Record<NoInterventionReason, number>>;
  suppressedRung3: SuppressedLeverRecord[];
  spendAvoidedInr: number;
  spendAvoidedByLever: Record<string, SpendAvoidedEntry>;
}

interface LedgerState {
  held: HeldDecisionRecord[];
  suppressedRung3: SuppressedLeverRecord[];
}

const STORAGE_KEY = "fk-intervention-ledger-v1";
const EMPTY_STATE: LedgerState = { held: [], suppressedRung3: [] };

class InterventionLedger {
  private state: LedgerState = this.load();
  private listeners = new Set<() => void>();
  /** Cached immutable snapshot so useSyncExternalStore doesn't loop. */
  private snapshot: LedgerSnapshot = this.buildSnapshot();

  private load(): LedgerState {
    if (typeof window === "undefined") return { ...EMPTY_STATE };
    try {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return { ...EMPTY_STATE };
      const parsed = JSON.parse(raw) as Partial<LedgerState>;
      return {
        held: parsed.held ?? [],
        suppressedRung3: parsed.suppressedRung3 ?? [],
      };
    } catch {
      // Corrupt or unavailable storage should never break the demo.
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

  getSnapshot = (): LedgerSnapshot => this.snapshot;

  private commit(): void {
    this.persist();
    this.snapshot = this.buildSnapshot();
    this.listeners.forEach((listener) => listener());
  }

  private buildSnapshot(): LedgerSnapshot {
    const heldByReason: Partial<Record<NoInterventionReason, number>> = {};
    for (const record of this.state.held) {
      heldByReason[record.reason] = (heldByReason[record.reason] ?? 0) + 1;
    }

    const spendAvoidedByLever: Record<string, SpendAvoidedEntry> = {};
    for (const record of this.state.suppressedRung3) {
      const unit = RUNG3_ASSUMED_VALUE_INR[record.leverId] ?? 0;
      const entry = spendAvoidedByLever[record.leverId] ?? {
        count: 0,
        assumedUnitValueInr: unit,
        totalInr: 0,
      };
      entry.count += 1;
      entry.totalInr += unit;
      spendAvoidedByLever[record.leverId] = entry;
    }
    const spendAvoidedInr = Object.values(spendAvoidedByLever).reduce(
      (sum, entry) => sum + entry.totalInr,
      0,
    );

    return {
      held: [...this.state.held],
      heldByReason,
      suppressedRung3: [...this.state.suppressedRung3],
      spendAvoidedInr,
      spendAvoidedByLever,
    };
  }

  /** One entry per "do nothing" decision — every hold from selectSurface, plus gate_held. */
  recordHeld(record: Omit<HeldDecisionRecord, "at">): void {
    this.state.held = [...this.state.held, { ...record, at: Date.now() }];
    this.commit();
  }

  /** One entry per rung-3 lever considered and suppressed in a single run. */
  recordSuppressedRung3(records: Array<{ leverId: string; reason: string }>): void {
    if (records.length === 0) return;
    const now = Date.now();
    this.state.suppressedRung3 = [
      ...this.state.suppressedRung3,
      ...records.map((record) => ({ ...record, at: now })),
    ];
    this.commit();
  }

  /** Demo control — mirrors `fatigueBudget.reset()` for a fresh run-through. */
  reset(): void {
    this.state = { ...EMPTY_STATE };
    this.commit();
  }
}

export const interventionLedger = new InterventionLedger();
