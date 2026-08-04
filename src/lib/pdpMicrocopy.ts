import type { Product, Seller } from "../types/product";
import { formatDeliveryDate } from "./format";
import { hasRecentPriceDrop } from "./priceHistory";

export function getAddToCartLabel(
  product: Product,
  seller: Seller,
  cause: string | null,
): string {
  if (
    cause === "cost_friction" &&
    product.signals?.priceHistory.length &&
    !hasRecentPriceDrop(product.signals.priceHistory, product.price.sellingPrice)
  ) {
    return "Add to Cart — price steady this week";
  }
  if (cause === "delivery_friction" && Number.isFinite(product.delivery.estimatedDays)) {
    return `Add to Cart — arrives ${formatDeliveryDate(product.delivery.estimatedDays)}`;
  }
  if (cause === "trust_friction") {
    if (product.badges.assured) return "Add to Cart — Flipkart Assured";
    if (Number.isFinite(seller.rating)) return `Add to Cart — ${seller.rating}★ seller`;
  }
  return "Add to Cart";
}
