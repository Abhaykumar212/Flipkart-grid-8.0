/**
 * What actually happens when a shopper accepts an intervention.
 *
 * Before this, "Claim Discount" / "Explore EMI Plans" etc. only scrolled the
 * page — the click had no real consequence, which is a dead end in a demo
 * where someone is meant to click it and see something happen. Each lever
 * below produces a concrete, visible result: a cart mutation (discount,
 * free/express delivery) plus a short-lived confirmation card describing it.
 *
 * Pure and side-effect-free — `InterventionContext` is the one place that
 * both calls this and applies `promo`/`freeDelivery`/`expressDelivery` to the
 * cart, so the displayed card and the actual cart total can never disagree.
 */

import { RUNG3_ASSUMED_VALUE_INR } from "./interventionPolicy";

export type OutcomeKind =
  | "discount"
  | "free_delivery"
  | "express_delivery"
  | "emi"
  | "price_alert"
  | "payment_saved"
  | "account_created"
  | "email_scheduled";

export interface InterventionOutcome {
  leverId: string;
  kind: OutcomeKind;
  title: string;
  body: string;
  detail?: string;
  /** Only for kind "discount" — the caller applies this to the cart. */
  promo?: { code: string; amountOff: number };
}

function randomCode(prefix: string): string {
  const digits = Math.floor(100 + Math.random() * 900);
  return `${prefix}${digits}`;
}

export interface OutcomeContext {
  cartValue: number;
  slowestDeliveryDays: number;
}

/** Returns `null` for levers with no concrete outcome (they only scroll, e.g. review_summary_surface). */
export function buildOutcome(leverId: string, ctx: OutcomeContext): InterventionOutcome | null {
  switch (leverId) {
    case "targeted_discount_code": {
      // Matches the ledger's own "promotional spend avoided" assumption
      // (RUNG3_ASSUMED_VALUE_INR) rather than a percent-of-cart formula that
      // scaled with basket size — a real margin lever shouldn't cost more the
      // more expensive the cart already is. Never exceeds the cart itself.
      const amountOff = Math.min(RUNG3_ASSUMED_VALUE_INR.targeted_discount_code, ctx.cartValue);
      const code = randomCode("GRID");
      return {
        leverId,
        kind: "discount",
        title: "Discount applied!",
        body: `${code} took ₹${amountOff} off this order — already reflected in your total.`,
        detail: "Valid for this session only.",
        promo: { code, amountOff },
      };
    }

    case "free_delivery_waiver":
      return {
        leverId,
        kind: "free_delivery",
        title: "Free delivery unlocked!",
        body: "Delivery charges have been waived on this order — check your cart total.",
      };

    case "delivery_speed_upgrade": {
      const fasterBy = Math.max(1, ctx.slowestDeliveryDays - 1);
      return {
        leverId,
        kind: "express_delivery",
        title: "Express delivery applied!",
        body: `Upgraded to express — arrives up to ${fasterBy === 1 ? "a day" : `${fasterBy} days`} sooner, on us.`,
      };
    }

    case "emi_plan_highlight": {
      const months = 6;
      const monthly = Math.max(1, Math.round(ctx.cartValue / months));
      return {
        leverId,
        kind: "emi",
        title: "No-Cost EMI ready",
        body: `Split into ${months} months at ₹${monthly.toLocaleString("en-IN")}/month, 0% interest.`,
        detail: "Select it as your payment method at checkout.",
      };
    }

    case "price_drop_alert":
      return {
        leverId,
        kind: "price_alert",
        title: "Price alert set",
        body: "We'll notify you the moment any item in your cart drops in price.",
      };

    case "saved_payment_prompt":
      return {
        leverId,
        kind: "payment_saved",
        title: "Payment method saved",
        body: "Your card is on file for one-tap checkout next time — no more re-entering details.",
      };

    case "guest_to_account_nudge":
      return {
        leverId,
        kind: "account_created",
        title: "You're signed in!",
        body: "Account created in one tap — order tracking and faster checkout are now available.",
      };

    case "abandoned_cart_email":
      return {
        leverId,
        kind: "email_scheduled",
        title: "Reminder scheduled",
        body: "We'll email you about this cart in a couple of hours if it's still waiting.",
      };

    default:
      return null;
  }
}
