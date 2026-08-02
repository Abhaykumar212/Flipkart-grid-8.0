import type { ShopperHistory, ScenarioSessionState } from "../lib/tracker";

/**
 * Deterministic demo scenarios.
 *
 * Each preset loads a cart AND overrides the shopper-profile assumptions, so a
 * given preset reliably produces a specific root cause. Without this you are at
 * the mercy of whatever the live session happens to look like when judges are
 * watching.
 *
 * The final preset is deliberately low-risk: it demonstrates the gate correctly
 * declining to spend an LLM call, which is as much a part of the design as the
 * analysis itself.
 */

export interface DemoScenario {
  id: string;
  label: string;
  /** What this preset is meant to demonstrate. */
  intent: string;
  expectedOutcome: string;
  /** Products to load, by catalog id. */
  cart: Array<{ productId: string; quantity: number }>;
  /** How long ago the cart was "added" — must clear the 10s warm-up gate. */
  cartAgeSeconds: number;
  history: Partial<ShopperHistory>;
  session: Partial<ScenarioSessionState>;
  accent: string;
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "cost-friction",
    label: "Cost shock",
    intent: "Expensive basket far above this shopper's norm, with a heavy delivery fee and failed coupon hunting.",
    expectedOutcome: "Targets cost_friction",
    cart: [{ productId: "p-1001", quantity: 1 }, { productId: "p-2003", quantity: 1 }],
    cartAgeSeconds: 400,
    history: {
      averageOrderValue: 4000,
      historicalAbandonmentRate: 0.72,
      pastReturnRate: 0.18,
      wishlistItemCount: 1,
      paymentMethodSaved: false,
      lifetimeOrdersPlaced: 2,
      daysSinceLastPurchase: 210,
      isGuestCheckout: true,
    },
    session: {
      failedCouponAttempts: 3,
      checkoutStepsCompleted: 0,
      cartPdpBounceCount: 2,
      idleBeforeCheckoutSeconds: 120,
    },
    accent: "from-rose-500 to-orange-500",
  },
  {
    id: "trust-friction",
    label: "Trust barrier",
    intent: "High-value cart, guest checkout, no saved payment method, brand-new shopper.",
    expectedOutcome: "Targets trust_friction",
    cart: [{ productId: "p-1005", quantity: 1 }],
    cartAgeSeconds: 300,
    history: {
      averageOrderValue: 12000,
      historicalAbandonmentRate: 0.6,
      pastReturnRate: 0.05,
      wishlistItemCount: 0,
      paymentMethodSaved: false,
      lifetimeOrdersPlaced: 0,
      daysSinceLastPurchase: 0,
      isGuestCheckout: true,
    },
    session: {
      checkoutStepsCompleted: 1,
      failedCouponAttempts: 0,
      cartPdpBounceCount: 1,
      idleBeforeCheckoutSeconds: 90,
    },
    accent: "from-amber-500 to-yellow-500",
  },
  {
    id: "delivery-friction",
    label: "Delivery anxiety",
    intent:
      "Slow promised delivery with repeated pincode checks. Cart value is kept close to the shopper's norm so cost does not dominate the diagnosis.",
    expectedOutcome: "Targets delivery_friction",
    cart: [{ productId: "p-5004", quantity: 1 }],
    cartAgeSeconds: 350,
    history: {
      // Deliberately close to the cart total (~₹32k) so
      // cart_value_vs_typical_order stays near 1.0 and the delivery signals
      // are what the model actually keys on.
      averageOrderValue: 30000,
      historicalAbandonmentRate: 0.7,
      pastReturnRate: 0.1,
      wishlistItemCount: 2,
      paymentMethodSaved: false,
      lifetimeOrdersPlaced: 2,
      daysSinceLastPurchase: 240,
      isGuestCheckout: true,
    },
    session: {
      pincodeCheckCount: 5,
      checkoutStepsCompleted: 0,
      cartPdpBounceCount: 3,
      idleBeforeCheckoutSeconds: 200,
    },
    accent: "from-sky-500 to-blue-600",
  },
  {
    id: "checkout-friction",
    label: "Checkout blocked",
    intent: "Shopper reached payment and hit repeated failures with no saved card.",
    expectedOutcome: "Targets checkout_friction",
    cart: [{ productId: "p-2001", quantity: 1 }],
    cartAgeSeconds: 500,
    history: {
      averageOrderValue: 30000,
      historicalAbandonmentRate: 0.5,
      pastReturnRate: 0.06,
      wishlistItemCount: 1,
      paymentMethodSaved: false,
      lifetimeOrdersPlaced: 6,
      daysSinceLastPurchase: 60,
      isGuestCheckout: true,
    },
    session: {
      paymentAttemptsFailed: 3,
      checkoutStepsCompleted: 2,
      failedCouponAttempts: 1,
      idleBeforeCheckoutSeconds: 200,
    },
    accent: "from-fuchsia-500 to-purple-600",
  },
  {
    id: "product-uncertainty",
    label: "Still deciding",
    intent: "Heavy comparison behaviour — many returns to the product page and deep review reading.",
    expectedOutcome: "Targets product_uncertainty",
    cart: [{ productId: "p-4002", quantity: 2 }, { productId: "p-4006", quantity: 1 }],
    cartAgeSeconds: 600,
    history: {
      averageOrderValue: 2000,
      historicalAbandonmentRate: 0.68,
      pastReturnRate: 0.28,
      wishlistItemCount: 6,
      paymentMethodSaved: false,
      lifetimeOrdersPlaced: 3,
      daysSinceLastPurchase: 150,
      isGuestCheckout: true,
    },
    session: {
      cartPdpBounceCount: 8,
      reviewsExpandedCount: 7,
      checkoutStepsCompleted: 0,
      idleBeforeCheckoutSeconds: 240,
    },
    accent: "from-teal-500 to-emerald-600",
  },
  {
    id: "low-risk-loyal",
    label: "Loyal shopper (gate holds)",
    intent: "Repeat customer, saved card, deep in checkout, modest basket. Proves the gate withholds the LLM call.",
    expectedOutcome: "Low risk → gate holds, no LLM call",
    cart: [{ productId: "p-4002", quantity: 1 }],
    cartAgeSeconds: 120,
    history: {
      averageOrderValue: 5000,
      historicalAbandonmentRate: 0.12,
      pastReturnRate: 0.02,
      wishlistItemCount: 3,
      paymentMethodSaved: true,
      lifetimeOrdersPlaced: 48,
      daysSinceLastPurchase: 6,
      isGuestCheckout: false,
    },
    session: {
      checkoutStepsCompleted: 3,
      cartPdpBounceCount: 0,
      reviewsExpandedCount: 0,
      failedCouponAttempts: 0,
      paymentAttemptsFailed: 0,
      idleBeforeCheckoutSeconds: 3,
    },
    accent: "from-emerald-500 to-green-600",
  },
];

export const scenarioById = new Map(DEMO_SCENARIOS.map((s) => [s.id, s]));
