import type { CartItem } from "../context/CartContext";
import { productById } from "../data/products";

/**
 * Discounted subtotal at or above this gets free delivery. Matches Flipkart's
 * real rule (orders under ₹500 are charged). Note the catalog's cheapest item
 * is ₹499, so this is also what keeps the paid-delivery branch reachable at all.
 */
export const FREE_DELIVERY_THRESHOLD = 500;
export const DELIVERY_CHARGE = 40;

export interface CartPerks {
  /** Flat rupee amount off, from an accepted `targeted_discount_code` intervention. */
  promoAmountOff?: number;
  promoLabel?: string;
  /** From an accepted `free_delivery_waiver` intervention. */
  freeDelivery?: boolean;
  /** From an accepted `delivery_speed_upgrade` intervention — informational only, no charge in this catalog. */
  expressDelivery?: boolean;
}

export interface CartTotals {
  /** Total quantity across all lines. */
  itemCount: number;
  /** Sum of MRP x quantity — the "Price (n items)" row. */
  totalMrp: number;
  /** Sum of selling price x quantity. */
  totalSellingPrice: number;
  discount: number;
  deliveryCharge: number;
  isDeliveryFree: boolean;
  totalAmount: number;
  /** What the green "You will save ..." line reports. */
  savings: number;
  /** Set when an intervention-granted promo reduced the total — separate from the catalog `discount`. */
  promoApplied: { label: string; amountOff: number } | null;
  expressDelivery: boolean;
}

/**
 * Pure derivation of the price summary from cart lines. Kept out of the
 * component so the summary card and later agent code share one calculation.
 * Cart entries whose product is missing from the catalog are skipped.
 *
 * `perks` is intervention-granted state (a claimed discount code, a waived
 * delivery fee) layered on top of the catalog numbers — kept as a separate,
 * optional argument so the ML feature pipeline (`TrackerContext`, which calls
 * this with no perks) keeps seeing the shopper's real, undiscounted cart.
 */
export function computeCartTotals(items: CartItem[], perks: CartPerks = {}): CartTotals {
  let itemCount = 0;
  let totalMrp = 0;
  let totalSellingPrice = 0;

  for (const item of items) {
    const product = productById.get(item.productId);
    if (!product) continue;

    itemCount += item.quantity;
    totalMrp += product.price.mrp * item.quantity;
    totalSellingPrice += product.price.sellingPrice * item.quantity;
  }

  const discount = totalMrp - totalSellingPrice;
  const isDeliveryFree =
    totalSellingPrice >= FREE_DELIVERY_THRESHOLD || totalSellingPrice === 0 || Boolean(perks.freeDelivery);
  const deliveryCharge = isDeliveryFree ? 0 : DELIVERY_CHARGE;

  // Never discount past zero, and never past the delivery charge that's about
  // to be added back on — a claimed code should still leave something to pay.
  const promoAmountOff = Math.min(perks.promoAmountOff ?? 0, totalSellingPrice);
  const promoApplied =
    promoAmountOff > 0 ? { label: perks.promoLabel ?? "Promo code", amountOff: promoAmountOff } : null;

  return {
    itemCount,
    totalMrp,
    totalSellingPrice,
    discount,
    deliveryCharge,
    isDeliveryFree,
    totalAmount: totalSellingPrice - promoAmountOff + deliveryCharge,
    savings: discount + promoAmountOff,
    promoApplied,
    expressDelivery: Boolean(perks.expressDelivery),
  };
}
