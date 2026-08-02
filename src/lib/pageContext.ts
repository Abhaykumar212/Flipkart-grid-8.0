/**
 * What the companion currently knows about where the shopper is — and,
 * crucially, where they've already been this session.
 *
 * Framework-independent, same subscribe/emit pattern as `SessionTracker` and
 * `UserHistoryStore`. Two different memories live here on purpose:
 *   - `pageContext` (this file): session-scoped, in-memory, gone on reload —
 *     "what has this browsing session looked at" (visit order, repeat visits,
 *     comparison candidates). This is *active* memory: it's what lets the
 *     companion notice "you've looked at three phones in this range" without
 *     being told.
 *   - `userHistory` (userHistory.ts): cross-session, localStorage-persisted —
 *     wishlist and long-term recently-viewed/purchased, unrelated to this
 *     session's live comparison behaviour.
 */

export interface ProductVisit {
  productId: string;
  title: string;
  brand: string;
  category: string;
  price: number;
  /** Epoch ms of the most recent visit. */
  lastVisitedAt: number;
  visitCount: number;
}

export interface PageContextSnapshot {
  /** The product currently on screen, or null off the PDP. */
  currentProductId: string | null;
  /**
   * Set once the shopper has held the reviews section in view for the dwell
   * threshold on the *current* product. Cleared on product change so it can
   * fire again for a different product later in the session.
   */
  reviewDwellProductId: string | null;
  /** Distinct products viewed this session, most-recently-visited first. */
  visitHistory: ProductVisit[];
  /** Raw search queries this session, most-recent first — real intent signal, not a count. */
  searchHistory: string[];
}

/** Bounds memory growth over a very long browsing session. */
const MAX_VISIT_HISTORY = 25;
const MAX_SEARCH_HISTORY = 15;
/** How many distinct same-category products count as "comparing", not browsing. */
const COMPARISON_MIN_PRODUCTS = 3;
/** "Similar price range" — ratio between the highest and lowest price considered. */
const COMPARISON_MAX_PRICE_RATIO = 1.6;

/**
 * Pure function, not store state, so it's directly testable: does this visit
 * history currently contain a comparison-worthy cluster? Looks at the most
 * recent visits only — an old, abandoned browsing thread from an hour ago
 * shouldn't resurrect itself as "you're comparing phones" right now.
 */
export function findComparisonCandidates(history: ProductVisit[]): ProductVisit[] | null {
  const recent = history.slice(0, 8);
  const byCategory = new Map<string, ProductVisit[]>();
  for (const visit of recent) {
    const bucket = byCategory.get(visit.category) ?? [];
    bucket.push(visit);
    byCategory.set(visit.category, bucket);
  }

  for (const bucket of byCategory.values()) {
    if (bucket.length < COMPARISON_MIN_PRODUCTS) continue;
    const prices = bucket.map((v) => v.price).filter((p) => p > 0);
    if (prices.length < COMPARISON_MIN_PRODUCTS) continue;
    const ratio = Math.max(...prices) / Math.min(...prices);
    if (ratio <= COMPARISON_MAX_PRICE_RATIO) {
      return bucket.slice(0, 3);
    }
  }
  return null;
}

class PageContextStore {
  private state: PageContextSnapshot = {
    currentProductId: null,
    reviewDwellProductId: null,
    visitHistory: [],
    searchHistory: [],
  };
  private listeners = new Set<() => void>();

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  private emit(): void {
    this.listeners.forEach((listener) => listener());
  }

  getSnapshot = (): PageContextSnapshot => this.state;

  setCurrentProduct(productId: string | null): void {
    if (this.state.currentProductId === productId) return;
    // Leaving a product clears its dwell flag so the signal is fresh if revisited.
    this.state = { ...this.state, currentProductId: productId, reviewDwellProductId: null };
    this.emit();
  }

  /** Records (or bumps) a product visit. Revisiting an earlier product moves it back to the front. */
  recordVisit(visit: Omit<ProductVisit, "lastVisitedAt" | "visitCount">): void {
    const existing = this.state.visitHistory.find((v) => v.productId === visit.productId);
    const entry: ProductVisit = {
      ...visit,
      lastVisitedAt: Date.now(),
      visitCount: (existing?.visitCount ?? 0) + 1,
    };
    const withoutExisting = this.state.visitHistory.filter((v) => v.productId !== visit.productId);
    this.state = {
      ...this.state,
      visitHistory: [entry, ...withoutExisting].slice(0, MAX_VISIT_HISTORY),
    };
    this.emit();
  }

  /** Records a real search query. Only dedupes an exact immediate repeat (e.g. a double-submit). */
  recordSearch(query: string): void {
    const trimmed = query.trim();
    if (!trimmed) return;
    if (this.state.searchHistory[0] === trimmed) return;
    this.state = {
      ...this.state,
      searchHistory: [trimmed, ...this.state.searchHistory].slice(0, MAX_SEARCH_HISTORY),
    };
    this.emit();
  }

  markReviewDwell(productId: string): void {
    if (this.state.currentProductId !== productId) return;
    if (this.state.reviewDwellProductId === productId) return;
    this.state = { ...this.state, reviewDwellProductId: productId };
    this.emit();
  }

  clearReviewDwell(): void {
    if (this.state.reviewDwellProductId === null) return;
    this.state = { ...this.state, reviewDwellProductId: null };
    this.emit();
  }
}

export const pageContext = new PageContextStore();
