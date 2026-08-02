/**
 * Lever -> target-anchor key(s), for the two surfaces that attach to a
 * specific page element (`inline`, `spotlight`). Levers not listed here render
 * without a target (`ambient`) or are delivered by `CompanionWidget`
 * (`companion`) — see `LEVER_POLICY` in `interventionPolicy.ts` for the surface
 * assignment itself.
 *
 * Keys are listed in preference order; only one will ever be mounted at a
 * time in practice (PDP and cart aren't both on screen at once), but the
 * order matters if that ever changes.
 */
export const LEVER_TARGET_KEYS: Partial<Record<string, string[]>> = {
  free_delivery_waiver: ["pdp-delivery", "cart-delivery-estimate"],
  delivery_speed_upgrade: ["pdp-delivery", "cart-delivery-estimate"],
  targeted_discount_code: ["pdp-price-block", "cart-price-block"],
  price_drop_alert: ["pdp-price-block", "cart-price-block"],
  emi_plan_highlight: ["pdp-emi-row"],
  review_summary_surface: ["reviews-header"],
  stock_scarcity_nudge: ["cart-similar-rail"],
};
