/**
 * Session telemetry for the cart-abandonment model.
 *
 * Emits exactly the 22 observable features the model was trained on, clamped to
 * the same ranges used during training so inference never sees out-of-distribution
 * values. Framework-independent so it can be reused outside React.
 */

export const ABANDONMENT_FEATURE_NAMES = [
  // A. Cart engagement
  "seconds_spent_in_cart",
  "times_returned_to_product_page",
  "product_reviews_read",
  "seconds_idle_before_checkout",
  "delivery_pincode_checks",
  "saved_items_in_wishlist",
  // B. Cost friction
  "cart_value_vs_typical_order",
  "delivery_fee_percent_of_cart",
  "price_dropped_since_first_view",
  "discount_seeking_tendency",
  "failed_coupon_attempts",
  // C. Delivery friction
  "estimated_delivery_days",
  // D. Checkout & trust friction
  "payment_method_on_file",
  "checkout_steps_completed",
  "payment_attempts_failed",
  "is_guest_checkout",
  // E. Customer history
  "past_abandonment_rate",
  "past_order_return_rate",
  "lifetime_orders_placed",
  "days_since_last_purchase",
  // F. Session context
  "is_mobile_session",
  "is_late_night_session",
] as const;

export type AbandonmentFeatureName = (typeof ABANDONMENT_FEATURE_NAMES)[number];

/**
 * Features that actually change a diagnosis. Mirrors MATERIAL_FEATURES in
 * backend/agents/root_cause.py.
 *
 * Deliberately excludes the continuously-ticking ones (seconds_spent_in_cart,
 * seconds_idle_before_checkout). Keying dedup on the full vector would make the
 * signature change every second, re-firing the agent on every poll.
 */
export const MATERIAL_FEATURE_NAMES: AbandonmentFeatureName[] = [
  "cart_value_vs_typical_order",
  "delivery_fee_percent_of_cart",
  "estimated_delivery_days",
  "payment_method_on_file",
  "checkout_steps_completed",
  "payment_attempts_failed",
  "is_guest_checkout",
  "failed_coupon_attempts",
  "times_returned_to_product_page",
  "product_reviews_read",
  "price_dropped_since_first_view",
];

/** Stable key over diagnosis-relevant features only. */
export function materialSignature(features: AbandonmentFeatures): string {
  return MATERIAL_FEATURE_NAMES.map(
    (name) => `${name}=${Math.round((features[name] ?? 0) * 1000) / 1000}`,
  ).join("|");
}

export type AbandonmentFeatures = {
  [Feature in AbandonmentFeatureName]: number;
};

export type RiskTier = "low" | "medium" | "high";

export interface PredictionResponse {
  abandonment_probability: number;
  confidence_score: number;
  risk_tier: RiskTier;
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

/**
 * Shopper profile. In production these come from the account service; until a
 * login exists they are neutral placeholders, and the UI labels them as such
 * rather than implying they are measured.
 */
export interface ShopperHistory {
  averageOrderValue: number;
  historicalAbandonmentRate: number;
  pastReturnRate: number;
  wishlistItemCount: number;
  paymentMethodSaved: boolean;
  lifetimeOrdersPlaced: number;
  daysSinceLastPurchase: number;
  isGuestCheckout: boolean;
}

export interface TrackerSignals {
  productVisits: number;
  searches: number;
  lastRoute: string;
  cartActive: boolean;
}

/** Session counters a demo scenario can pre-seed. */
export interface ScenarioSessionState {
  cartPdpBounceCount: number;
  reviewsExpandedCount: number;
  pincodeCheckCount: number;
  failedCouponAttempts: number;
  checkoutStepsCompleted: number;
  paymentAttemptsFailed: number;
  idleBeforeCheckoutSeconds: number;
}

/** Cart state sent alongside the features so the agent can be concrete. */
export interface CartContextPayload {
  lines: Array<{
    product_id: string;
    title: string;
    brand: string;
    category: string;
    quantity: number;
    selling_price: number;
    mrp: number;
    discount_percent: number;
    estimated_delivery_days: number;
    in_stock: boolean;
    price_dropped_recently: boolean;
  }>;
  cart_total: number;
  mrp_total: number;
  delivery_fee: number;
  currency: string;
  cart_age_seconds: number;
  current_route: string;
}

export interface TrackerSnapshot {
  features: AbandonmentFeatures;
  signals: TrackerSignals;
}

const API_BASE = "http://localhost:8000";
const PREDICTION_URL = `${API_BASE}/api/predict-abandonment`;
const ROOT_CAUSE_URL = `${API_BASE}/api/root-cause-analysis`;

/** Stable per-browser-tab id so the backend can dedupe and budget per session. */
function resolveSessionId(): string {
  if (typeof window === "undefined") return "server";
  const KEY = "fk-pipeline-session-id";
  let id = window.sessionStorage.getItem(KEY);
  if (!id) {
    id = `sess_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    window.sessionStorage.setItem(KEY, id);
  }
  return id;
}

export const SESSION_ID = resolveSessionId();

const DEFAULT_HISTORY: ShopperHistory = {
  // Placeholder until an account service exists. Set to a value representative
  // of this (electronics-heavy) catalog so `cart_value_vs_typical_order` varies
  // meaningfully across carts instead of saturating at its clamp on every session.
  averageOrderValue: 15000,
  historicalAbandonmentRate: 0.45,
  pastReturnRate: 0.08,
  wishlistItemCount: 0,
  paymentMethodSaved: false,
  lifetimeOrdersPlaced: 3,
  daysSinceLastPurchase: 45,
  isGuestCheckout: true,
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

/** Checkout is a 3-step funnel: address -> summary -> payment. */
function checkoutStepFromRoute(pathname: string): number {
  return pathname.startsWith("/checkout") ? 1 : 0;
}

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
  private failedCouponAttempts = 0;
  private checkoutStepsCompleted = 0;
  private paymentAttemptsFailed = 0;
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

    this.checkoutStepsCompleted = Math.max(
      this.checkoutStepsCompleted,
      checkoutStepFromRoute(pathname),
    );

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
      this.checkoutStepsCompleted = 0;
      this.paymentAttemptsFailed = 0;
      this.failedCouponAttempts = 0;
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

  /** Advance the checkout funnel: 1 = address, 2 = summary, 3 = payment. */
  recordCheckoutStep(step: number, at = Date.now()): void {
    this.checkoutStepsCompleted = Math.min(
      3,
      Math.max(this.checkoutStepsCompleted, Math.round(step)),
    );
    this.markActivity(at);
    this.emit();
  }

  recordFailedCoupon(at = Date.now()): void {
    this.failedCouponAttempts = Math.min(6, this.failedCouponAttempts + 1);
    this.markActivity(at);
    this.emit();
  }

  recordFailedPayment(at = Date.now()): void {
    this.paymentAttemptsFailed = Math.min(5, this.paymentAttemptsFailed + 1);
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

    const hour = new Date(now).getHours();
    const isLateNight = hour >= 23 || hour < 5;
    // Coarse but honest: viewport width is the signal actually available
    // client-side without a UA-parsing dependency.
    const isMobile = typeof window !== "undefined" && window.innerWidth < 768;

    const features: AbandonmentFeatures = {
      // A. Cart engagement
      seconds_spent_in_cart: this.cart.itemCount > 0
        ? clamp(cartDwellSeconds, 0, 900)
        : 0,
      times_returned_to_product_page: Math.round(clamp(this.cartPdpBounceCount, 0, 10)),
      product_reviews_read: Math.round(clamp(this.reviewsExpandedCount, 0, 8)),
      seconds_idle_before_checkout: rounded(clamp(idleSeconds, 0, 300), 2),
      delivery_pincode_checks: Math.round(clamp(this.pincodeCheckCount, 0, 5)),
      saved_items_in_wishlist: Math.round(clamp(this.history.wishlistItemCount, 0, 20)),

      // B. Cost friction
      cart_value_vs_typical_order: rounded(clamp(
        this.history.averageOrderValue > 0
          ? this.cart.cartValue / this.history.averageOrderValue
          : 1,
        0,
        6,
      )),
      delivery_fee_percent_of_cart: rounded(clamp(
        this.cart.cartValue > 0
          ? (this.cart.deliveryFee / this.cart.cartValue) * 100
          : 0,
        0,
        25,
      ), 2),
      price_dropped_since_first_view: this.cart.products.some(
        (product) => product.priceDroppedRecently,
      ) ? 1 : 0,
      discount_seeking_tendency: rounded(clamp(discountSensitivity, 0, 1)),
      failed_coupon_attempts: Math.round(clamp(this.failedCouponAttempts, 0, 6)),

      // C. Delivery friction
      estimated_delivery_days: Math.round(clamp(this.cart.products.reduce(
        (longest, product) => Math.max(longest, product.estimatedDeliveryDays),
        1,
      ), 1, 10)),

      // D. Checkout & trust friction
      payment_method_on_file: this.history.paymentMethodSaved ? 1 : 0,
      checkout_steps_completed: Math.round(clamp(this.checkoutStepsCompleted, 0, 3)),
      payment_attempts_failed: Math.round(clamp(this.paymentAttemptsFailed, 0, 5)),
      is_guest_checkout: this.history.isGuestCheckout ? 1 : 0,

      // E. Customer history
      past_abandonment_rate: rounded(clamp(this.history.historicalAbandonmentRate, 0, 1)),
      past_order_return_rate: rounded(clamp(this.history.pastReturnRate, 0, 0.5)),
      lifetime_orders_placed: Math.round(clamp(this.history.lifetimeOrdersPlaced, 0, 120)),
      days_since_last_purchase: rounded(clamp(this.history.daysSinceLastPurchase, 0, 400), 1),

      // F. Session context
      is_mobile_session: isMobile ? 1 : 0,
      is_late_night_session: isLateNight ? 1 : 0,
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

  /** Overwrite shopper-profile assumptions — used by the demo scenario presets. */
  applyScenario(history: Partial<ShopperHistory>, session: Partial<ScenarioSessionState> = {}): void {
    this.history = { ...this.history, ...history };
    if (session.cartPdpBounceCount !== undefined) {
      this.cartPdpBounceCount = session.cartPdpBounceCount;
    }
    if (session.reviewsExpandedCount !== undefined) {
      this.reviewsExpandedCount = session.reviewsExpandedCount;
    }
    if (session.pincodeCheckCount !== undefined) {
      this.pincodeCheckCount = session.pincodeCheckCount;
    }
    if (session.failedCouponAttempts !== undefined) {
      this.failedCouponAttempts = session.failedCouponAttempts;
    }
    if (session.checkoutStepsCompleted !== undefined) {
      this.checkoutStepsCompleted = session.checkoutStepsCompleted;
    }
    if (session.paymentAttemptsFailed !== undefined) {
      this.paymentAttemptsFailed = session.paymentAttemptsFailed;
    }
    if (session.idleBeforeCheckoutSeconds !== undefined) {
      this.idleBeforeCheckoutSeconds = session.idleBeforeCheckoutSeconds;
      this.checkoutStarted = true;
    }
    this.emit();
  }

  /** Reset scenario-injected state back to a clean session. */
  resetScenario(): void {
    this.history = { ...DEFAULT_HISTORY };
    this.cartPdpBounceCount = 0;
    this.reviewsExpandedCount = 0;
    this.pincodeCheckCount = 0;
    this.failedCouponAttempts = 0;
    this.checkoutStepsCompleted = 0;
    this.paymentAttemptsFailed = 0;
    this.idleBeforeCheckoutSeconds = 0;
    this.checkoutStarted = false;
    this.emit();
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

  /**
   * Phase 2. The backend re-runs inference itself and owns the trigger decision,
   * so a non-firing gate is a normal 200 response, not an error.
   */
  async requestRootCause(
    cartContext: CartContextPayload,
    options: { force?: boolean; signal?: AbortSignal } = {},
  ): Promise<unknown> {
    const snapshot = this.getSnapshot();
    const response = await fetch(ROOT_CAUSE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        features: snapshot.features,
        cart_context: cartContext,
        session_id: SESSION_ID,
        force: Boolean(options.force),
      }),
      signal: options.signal,
    });

    if (!response.ok) {
      throw new Error(`Root cause API returned ${response.status}`);
    }
    return response.json();
  }
}

export const sessionTracker = new SessionTracker();
