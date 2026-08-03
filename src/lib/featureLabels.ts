/**
 * Short human labels for the 67 serving features.
 *
 * The backend owns the full sentences used in the explanation trail; these are
 * the compact noun phrases the dashboard needs for chips, table cells, and the
 * feature snapshot grid. A raw identifier on screen is a defect either way.
 */

export const NARRATIVE_LABELS: Record<string, string> = {
  // User history
  u_lifetime_orders: "Lifetime orders",
  u_prior_abandonment_rate: "Prior abandonment rate",
  u_avg_order_value: "Typical order value",
  u_discount_usage_rate: "Discount usage",
  u_category_affinity: "Category affinity",
  u_days_since_last_purchase: "Days since last purchase",
  u_avg_session_to_purchase_s: "Usual time to purchase",
  u_return_rate: "Return rate",
  u_is_new_user: "New shopper",
  u_affinity_informational: "Responds to information",
  u_affinity_incentive: "Responds to incentives",
  // Cart
  c_value: "Cart value",
  c_item_count: "Items in cart",
  c_distinct_categories: "Categories in cart",
  c_value_to_aov_ratio: "Cart vs typical order",
  c_discount_pct_available: "Advertised discount",
  c_age_seconds: "Cart age",
  c_promo_applied: "Promo applied",
  c_max_price_drop_pct: "Largest price drop",
  c_price_increased_since_view: "Price rose since view",
  // Product
  p_max_item_price: "Priciest item",
  p_avg_rating: "Average rating",
  p_min_rating_count: "Fewest ratings",
  p_any_low_stock: "Low stock",
  p_any_out_of_stock: "Out of stock",
  // Delivery
  d_max_days: "Slowest delivery",
  d_min_days: "Fastest delivery",
  d_fee: "Delivery fee",
  d_fee_pct_of_cart: "Delivery as % of cart",
  d_check_count: "Delivery checks",
  // Payment
  pay_method_on_file: "Saved payment method",
  pay_failure_count: "Failed payments",
  pay_method_change_count: "Payment switches",
  pay_emi_eligible: "EMI eligible",
  pay_checkout_max_step: "Furthest checkout step",
  // Session behaviour
  s_duration_seconds: "Session length",
  s_product_view_count: "Product views",
  s_distinct_products_viewed: "Distinct products",
  s_review_open_count: "Review opens",
  s_review_dwell_seconds: "Time reading reviews",
  s_similar_product_view_count: "Similar products viewed",
  s_comparison_count: "Comparisons",
  s_cart_view_count: "Cart revisits",
  s_cart_add_count: "Cart adds",
  s_cart_remove_count: "Cart removes",
  s_cart_product_switch_count: "Cart item swaps",
  s_search_count: "Searches",
  s_price_sort_count: "Price sorts",
  s_coupon_search_count: "Coupon searches",
  s_checkout_start_count: "Checkout starts",
  s_back_from_checkout_count: "Checkout exits",
  s_idle_seconds_current: "Idle time",
  s_event_velocity_per_min: "Actions per minute",
  // Context
  x_is_mobile: "On mobile",
  x_hour_of_day: "Hour of day",
  x_is_late_night: "Late night",
  x_is_weekend: "Weekend",
  x_is_returning_user: "Returning visitor",
  x_referral_direct: "Direct arrival",
  x_referral_search: "From search",
  x_referral_social: "From social",
  x_referral_email: "From email",
  // Intervention history
  i_shown_count: "Nudges shown",
  i_dismissal_count: "Nudges dismissed",
  i_click_count: "Nudges engaged",
  i_seconds_since_last: "Since last nudge",
  i_distinct_types_shown: "Distinct nudge types",
};

/** Feature group headings, keyed by identifier prefix. */
export const FEATURE_GROUPS: Array<{ prefix: string; label: string }> = [
  { prefix: "u_", label: "Shopper history" },
  { prefix: "c_", label: "Cart" },
  { prefix: "p_", label: "Product" },
  { prefix: "d_", label: "Delivery" },
  { prefix: "pay_", label: "Payment" },
  { prefix: "s_", label: "Session behaviour" },
  { prefix: "x_", label: "Context" },
  { prefix: "i_", label: "Intervention history" },
];

export function featureLabel(name: string): string {
  return NARRATIVE_LABELS[name] ?? name.replaceAll("_", " ");
}

/** Which group a feature belongs to, matching the longest prefix first. */
export function featureGroup(name: string): string {
  const match = [...FEATURE_GROUPS]
    .sort((left, right) => right.prefix.length - left.prefix.length)
    .find((group) => name.startsWith(group.prefix));
  return match?.label ?? "Other";
}
