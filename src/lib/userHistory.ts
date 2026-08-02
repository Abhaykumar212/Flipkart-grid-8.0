/**
 * Real (if lightweight) shopper history, replacing the scalar placeholders
 * `ShopperHistory.wishlistItemCount` etc. used to be. Persisted to
 * localStorage — not sessionStorage — so it survives across tabs and reloads
 * the way an account-backed history would, without requiring the auth system
 * this demo doesn't have.
 *
 * Framework-independent, same subscribe/emit pattern as `SessionTracker` in
 * `tracker.ts`, so it can be read outside React (e.g. when assembling the
 * ShopperProfile sent to the backend).
 */

const STORAGE_KEY = "fk-user-history-v1";
const MAX_RECENT_VIEWS = 20;

export interface UserHistorySnapshot {
  /** Most-recently-viewed product ids first, deduplicated. */
  recentViewProductIds: string[];
  /** Product ids from completed (mock) orders. */
  pastPurchaseProductIds: string[];
}

const EMPTY: UserHistorySnapshot = { recentViewProductIds: [], pastPurchaseProductIds: [] };

function readStored(): UserHistorySnapshot {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY };
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return { ...EMPTY };
    const candidate = parsed as Partial<UserHistorySnapshot>;
    return {
      recentViewProductIds: Array.isArray(candidate.recentViewProductIds)
        ? candidate.recentViewProductIds.filter((id): id is string => typeof id === "string")
        : [],
      pastPurchaseProductIds: Array.isArray(candidate.pastPurchaseProductIds)
        ? candidate.pastPurchaseProductIds.filter((id): id is string => typeof id === "string")
        : [],
    };
  } catch {
    return { ...EMPTY };
  }
}

class UserHistoryStore {
  private state: UserHistorySnapshot = readStored();
  private listeners = new Set<() => void>();

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private persist(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
    } catch {
      // Storage full or unavailable (private mode) — in-memory state still works.
    }
    this.listeners.forEach((listener) => listener());
  }

  getSnapshot(): UserHistorySnapshot {
    return this.state;
  }

  recordView(productId: string): void {
    const withoutExisting = this.state.recentViewProductIds.filter((id) => id !== productId);
    this.state = {
      ...this.state,
      recentViewProductIds: [productId, ...withoutExisting].slice(0, MAX_RECENT_VIEWS),
    };
    this.persist();
  }

  recordPurchase(productIds: string[]): void {
    if (productIds.length === 0) return;
    const merged = [...this.state.pastPurchaseProductIds];
    for (const id of productIds) {
      if (!merged.includes(id)) merged.push(id);
    }
    this.state = { ...this.state, pastPurchaseProductIds: merged };
    this.persist();
  }
}

export const userHistory = new UserHistoryStore();
