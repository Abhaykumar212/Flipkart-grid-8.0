import type { CartItem } from "../context/CartContext";
import { productById } from "../data/products";

/**
 * Discounted subtotal at or above this gets free delivery. Matches Flipkart's
 * real rule (orders under ₹500 are charged). Note the catalog's cheapest item
 * is ₹499, so this is also what keeps the paid-delivery branch reachable at all.
 */
export const FREE_DELIVERY_THRESHOLD = 500;
export const DELIVERY_CHARGE = 40;

export const PROMO_CODES = {
  WELCOME10: "10% off up to ₹500",
  FLIPKART200: "₹200 off orders above ₹2,000",
} as const;

export interface CartTotals {
  /** Total quantity across all lines. */
  itemCount: number;
  /** Sum of MRP x quantity — the "Price (n items)" row. */
  totalMrp: number;
  /** Sum of selling price x quantity. */
  totalSellingPrice: number;
  discount: number;
  productDiscount: number;
  promoDiscount: number;
  deliveryCharge: number;
  isDeliveryFree: boolean;
  totalAmount: number;
  /** What the green "You will save ..." line reports. */
  savings: number;
}

/**
 * Pure derivation of the price summary from cart lines. Kept out of the
 * component so the summary card and later agent code share one calculation.
 * Cart entries whose product is missing from the catalog are skipped.
 */
export function computeCartTotals(
  items: CartItem[],
  promoCode: string | null = null,
  shippingSurcharge = 0,
): CartTotals {
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

  const productDiscount = totalMrp - totalSellingPrice;
  const normalizedPromo = promoCode?.toUpperCase();
  const promoDiscount = normalizedPromo === "WELCOME10"
    ? Math.min(500, Math.round(totalSellingPrice * 0.1))
    : normalizedPromo === "FLIPKART200" && totalSellingPrice >= 2000
      ? 200
      : 0;
  const discount = productDiscount + promoDiscount;
  const isDeliveryFree =
    totalSellingPrice >= FREE_DELIVERY_THRESHOLD || totalSellingPrice === 0;
  const deliveryCharge = (isDeliveryFree ? 0 : DELIVERY_CHARGE) + shippingSurcharge;

  return {
    itemCount,
    totalMrp,
    totalSellingPrice,
    discount,
    deliveryCharge,
    isDeliveryFree,
    totalAmount: Math.max(0, totalSellingPrice + deliveryCharge - promoDiscount),
    savings: discount,
    productDiscount,
    promoDiscount,
  };
}
