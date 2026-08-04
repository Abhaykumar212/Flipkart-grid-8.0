export interface ProductVisit {
  productId: string;
  title: string;
  category: string;
  price: number;
  lastVisitedAt: number;
  visitCount: number;
}

export interface CompanionRequest {
  id: number;
  prompt?: string;
}

export interface ShoppingContextSnapshot {
  currentProductId: string | null;
  reviewDwellProductId: string | null;
  visitHistory: ProductVisit[];
  searchHistory: string[];
  companionRequest: CompanionRequest | null;
}

const MAX_VISITS = 24;
const MAX_SEARCHES = 12;
const COMPARISON_MIN_PRODUCTS = 3;
const COMPARISON_MAX_PRICE_RATIO = 1.6;

const EMPTY_SNAPSHOT: ShoppingContextSnapshot = {
  currentProductId: null,
  reviewDwellProductId: null,
  visitHistory: [],
  searchHistory: [],
  companionRequest: null,
};

export function findComparisonCandidates(history: ProductVisit[]): ProductVisit[] | null {
  const byCategory = new Map<string, ProductVisit[]>();
  for (const visit of history.slice(0, 8)) {
    const candidates = byCategory.get(visit.category) ?? [];
    candidates.push(visit);
    byCategory.set(visit.category, candidates);
  }

  for (const candidates of byCategory.values()) {
    if (candidates.length < COMPARISON_MIN_PRODUCTS) continue;
    const prices = candidates.map((item) => item.price).filter((price) => price > 0);
    if (prices.length < COMPARISON_MIN_PRODUCTS) continue;
    if (Math.max(...prices) / Math.min(...prices) <= COMPARISON_MAX_PRICE_RATIO) {
      return candidates.slice(0, COMPARISON_MIN_PRODUCTS);
    }
  }
  return null;
}

export class ShoppingContextStore {
  private state: ShoppingContextSnapshot = EMPTY_SNAPSHOT;
  private listeners = new Set<() => void>();
  private nextRequestId = 1;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getSnapshot = (): ShoppingContextSnapshot => this.state;

  setCurrentProduct(productId: string | null): void {
    if (this.state.currentProductId === productId) return;
    this.update({
      ...this.state,
      currentProductId: productId,
      reviewDwellProductId: null,
    });
  }

  recordVisit(visit: Omit<ProductVisit, "lastVisitedAt" | "visitCount">): void {
    const previous = this.state.visitHistory.find((item) => item.productId === visit.productId);
    const nextVisit: ProductVisit = {
      ...visit,
      lastVisitedAt: Date.now(),
      visitCount: (previous?.visitCount ?? 0) + 1,
    };
    this.update({
      ...this.state,
      visitHistory: [
        nextVisit,
        ...this.state.visitHistory.filter((item) => item.productId !== visit.productId),
      ].slice(0, MAX_VISITS),
    });
  }

  recordSearch(query: string): void {
    const normalized = query.trim();
    if (!normalized || this.state.searchHistory[0] === normalized) return;
    this.update({
      ...this.state,
      searchHistory: [normalized, ...this.state.searchHistory].slice(0, MAX_SEARCHES),
    });
  }

  markReviewDwell(productId: string): void {
    if (
      this.state.currentProductId !== productId
      || this.state.reviewDwellProductId === productId
    ) return;
    this.update({ ...this.state, reviewDwellProductId: productId });
  }

  requestCompanion(prompt?: string): void {
    this.update({
      ...this.state,
      companionRequest: { id: this.nextRequestId++, ...(prompt ? { prompt } : {}) },
    });
  }

  resetForTests(): void {
    this.state = EMPTY_SNAPSHOT;
    this.nextRequestId = 1;
    this.emit();
  }

  private update(next: ShoppingContextSnapshot): void {
    this.state = next;
    this.emit();
  }

  private emit(): void {
    this.listeners.forEach((listener) => listener());
  }
}

export const shoppingContext = new ShoppingContextStore();
