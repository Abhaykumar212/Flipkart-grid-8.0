export const ABANDONMENT_FEATURE_NAMES = [
  "cart_dwell_time_seconds",
  "cart_pdp_bounce_count",
  "reviews_expanded_count",
  "idle_time_before_checkout",
  "delivery_pincode_checked",
  "cart_value_to_aov_ratio",
  "delivery_fee_percentage",
  "est_delivery_days",
  "has_price_dropped_recently",
  "hist_abandonment_rate",
  "discount_sensitivity_score",
  "past_return_rate",
  "wishlist_item_count",
  "payment_method_saved",
] as const;

export type AbandonmentFeatureName = (typeof ABANDONMENT_FEATURE_NAMES)[number];

export type AbandonmentFeatures = {
  [Feature in AbandonmentFeatureName]: number;
};

export interface PredictionResponse {
  abandonment_probability: number;
  confidence_score: number;
  top_contributing_features: Array<{
    feature: string;
    shap_value: number;
  }>;
  feature_impacts: Record<string, number>;
  status: "success";
}

export interface TrackedCartProduct {
  id: string;
  quantity: number;
  sellingPrice: number;
  mrp: number;
  deliveryFee: number;
  estimatedDeliveryDays: number;
  priceDroppedRecently: boolean;
  addedAt: string;
}

export interface CartSnapshot {
  products: TrackedCartProduct[];
  itemCount: number;
  cartValue: number;
  deliveryFee: number;
}

export interface ShopperHistory {
  averageOrderValue: number;
  historicalAbandonmentRate: number;
  pastReturnRate: number;
  wishlistItemCount: number;
  paymentMethodSaved: boolean;
}

export interface TrackerSignals {
  productVisits: number;
  searches: number;
  lastRoute: string;
  cartActive: boolean;
}

export interface TrackerSnapshot {
  features: AbandonmentFeatures;
  signals: TrackerSignals;
}

const PREDICTION_URL = "http://localhost:8000/api/predict-abandonment";
const DEFAULT_HISTORY: ShopperHistory = {
  // Neutral fallbacks used until an authenticated shopper profile is loaded.
  averageOrderValue: 2500,
  historicalAbandonmentRate: 0.45,
  pastReturnRate: 0.08,
  wishlistItemCount: 0,
  paymentMethodSaved: false,
};

const EMPTY_CART: CartSnapshot = {
  products: [],
  itemCount: 0,
  cartValue: 0,
  deliveryFee: 0,
};

function finite(value: number): number {
  return Number.isFinite(value) ? value : 0;
}

function rounded(value: number, digits = 4): number {
  return Number(finite(value).toFixed(digits));
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, finite(value)));
}

function isCartRoute(pathname: string): boolean {
  return pathname === "/cart" || pathname.startsWith("/cart/");
}

function isPdpRoute(pathname: string): boolean {
  return pathname.startsWith("/product/");
}

/**
 * Framework-independent telemetry store for the Phase 1 abandonment model.
 * It emits only the model's 14 documented features and can be used outside React.
 */
export class SessionTracker {
  private cart: CartSnapshot = EMPTY_CART;
  private history: ShopperHistory;
  private previousRoute = "";
  private cartPdpBounceCount = 0;
  private reviewsExpandedCount = 0;
  private productVisits = 0;
  private lastProductVisit: { productId: string; at: number } | null = null;
  private searches = 0;
  private pincodeCheckCount = 0;
  private lastActivityAt = Date.now();
  private idleBeforeCheckoutSeconds = 0;
  private checkoutStarted = false;
  private listeners = new Set<() => void>();

  constructor(history: Partial<ShopperHistory> = {}) {
    this.history = { ...DEFAULT_HISTORY, ...history };
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(): void {
    this.listeners.forEach((listener) => listener());
  }

  private markActivity(at = Date.now()): void {
    this.lastActivityAt = at;
  }

  recordRoute(pathname: string, at = Date.now()): void {
    if (pathname === this.previousRoute) return;

    const movedBetweenCartAndPdp =
      (isCartRoute(this.previousRoute) && isPdpRoute(pathname))
      || (isPdpRoute(this.previousRoute) && isCartRoute(pathname));
    if (movedBetweenCartAndPdp) {
      this.cartPdpBounceCount = Math.min(10, this.cartPdpBounceCount + 1);
    }

    if (pathname.startsWith("/checkout") && !this.checkoutStarted) {
      this.idleBeforeCheckoutSeconds = Math.max(
        0,
        Math.round((at - this.lastActivityAt) / 1_000),
      );
      this.checkoutStarted = true;
    }

    this.previousRoute = pathname;
    this.markActivity(at);
    this.emit();
  }

  recordCart(snapshot: CartSnapshot, at = Date.now()): void {
    const wasActive = this.cart.itemCount > 0;
    this.cart = snapshot;
    if (snapshot.itemCount === 0) {
      this.checkoutStarted = false;
      this.pincodeCheckCount = 0;
    }
    if (snapshot.itemCount > 0 || wasActive) this.markActivity(at);
    this.emit();
  }

  recordProductVisit(productId: string, at = Date.now()): void {
    if (
      this.lastProductVisit?.productId === productId &&
      at - this.lastProductVisit.at < 1_000
    ) return;

    this.lastProductVisit = { productId, at };
    this.productVisits += 1;
    this.markActivity(at);
    this.emit();
  }

  recordReviewVisibility(at = Date.now()): void {
    this.reviewsExpandedCount = Math.min(8, this.reviewsExpandedCount + 1);
    this.markActivity(at);
    this.emit();
  }

  recordSearch(_query: string, at = Date.now()): void {
    this.searches += 1;
    this.markActivity(at);
    this.emit();
  }

  recordPincodeCheck(_pincode: string, at = Date.now()): void {
    this.pincodeCheckCount = Math.min(5, this.pincodeCheckCount + 1);
    this.markActivity(at);
    this.emit();
  }

  recordActivity(at = Date.now()): void {
    this.markActivity(at);
    this.emit();
  }

  getSnapshot(now = Date.now()): TrackerSnapshot {
    const oldestAddedAt = this.cart.products.reduce<number | null>((oldest, product) => {
      const timestamp = Date.parse(product.addedAt);
      if (!Number.isFinite(timestamp)) return oldest;
      return oldest === null ? timestamp : Math.min(oldest, timestamp);
    }, null);
    const cartDwellSeconds = oldestAddedAt === null
      ? 0
      : Math.max(0, Math.floor((now - oldestAddedAt) / 1_000));
    const totalMrp = this.cart.products.reduce(
      (sum, product) => sum + product.mrp * product.quantity,
      0,
    );
    const discountRate = totalMrp > 0
      ? Math.max(0, (totalMrp - this.cart.cartValue) / totalMrp)
      : 0;
    const searchFactor = Math.min(this.searches / 5, 1);
    const discountSensitivity = Math.min(1, discountRate * 0.8 + searchFactor * 0.2);
    const idleSeconds = this.checkoutStarted
      ? this.idleBeforeCheckoutSeconds
      : Math.max(0, Math.floor((now - this.lastActivityAt) / 1_000));

    const features: AbandonmentFeatures = {
      cart_dwell_time_seconds: this.cart.itemCount > 0
        ? clamp(cartDwellSeconds, 10, 600)
        : 10,
      cart_pdp_bounce_count: Math.round(clamp(this.cartPdpBounceCount, 0, 10)),
      reviews_expanded_count: Math.round(clamp(this.reviewsExpandedCount, 0, 8)),
      idle_time_before_checkout: rounded(clamp(idleSeconds, 0, 300), 2),
      delivery_pincode_checked: Math.round(clamp(this.pincodeCheckCount, 0, 5)),
      cart_value_to_aov_ratio: rounded(clamp(
        this.history.averageOrderValue > 0
          ? this.cart.cartValue / this.history.averageOrderValue
          : 1,
        0.2,
        4,
      )),
      delivery_fee_percentage: rounded(clamp(
        this.cart.cartValue > 0
          ? (this.cart.deliveryFee / this.cart.cartValue) * 100
          : 0,
        0,
        15,
      ), 2),
      est_delivery_days: Math.round(clamp(this.cart.products.reduce(
        (longest, product) => Math.max(longest, product.estimatedDeliveryDays),
        1,
      ), 1, 10)),
      has_price_dropped_recently: this.cart.products.some(
        (product) => product.priceDroppedRecently,
      ) ? 1 : 0,
      hist_abandonment_rate: rounded(clamp(this.history.historicalAbandonmentRate, 0, 1)),
      discount_sensitivity_score: rounded(clamp(discountSensitivity, 0, 1)),
      past_return_rate: rounded(clamp(this.history.pastReturnRate, 0, 0.5)),
      wishlist_item_count: Math.round(clamp(this.history.wishlistItemCount, 0, 5)),
      payment_method_saved: this.history.paymentMethodSaved ? 1 : 0,
    };

    return {
      features,
      signals: {
        productVisits: this.productVisits,
        searches: this.searches,
        lastRoute: this.previousRoute,
        cartActive: this.cart.itemCount > 0 && this.cart.cartValue > 0,
      },
    };
  }

  async predict(signal?: AbortSignal): Promise<PredictionResponse> {
    const snapshot = this.getSnapshot();
    if (!snapshot.signals.cartActive) {
      throw new Error("Abandonment prediction requires an active cart");
    }

    const response = await fetch(PREDICTION_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(snapshot.features),
      signal,
    });

    if (!response.ok) {
      throw new Error(`Prediction API returned ${response.status}`);
    }

    const result = (await response.json()) as PredictionResponse;
    if (result.status !== "success") {
      throw new Error("Prediction API returned an unsuccessful response");
    }
    return result;
  }
}

export const sessionTracker = new SessionTracker();
