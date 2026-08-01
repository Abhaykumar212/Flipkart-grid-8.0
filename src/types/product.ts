/**
 * Product shape mirrors Flipkart's listing payload closely enough that the UI
 * reads as real inventory, while `signals` gives the cart-abandonment agent a
 * typed extension surface it can populate without a data migration.
 */

export type CategorySlug =
  | "mobiles"
  | "electronics"
  | "audio"
  | "appliances"
  | "fashion";

export interface Price {
  mrp: number;
  sellingPrice: number;
  currency: "INR";
}

export interface Rating {
  value: number;
  /** Number of star ratings. */
  count: number;
  /** Number of written reviews. */
  reviewCount: number;
}

export interface Badges {
  assured: boolean;
  bestseller: boolean;
  sponsored: boolean;
}

export interface Delivery {
  free: boolean;
  estimatedDays: number;
  express: boolean;
}

export interface Emi {
  monthly: number;
  months: number;
}

export interface Stock {
  inStock: boolean;
  quantityLeft: number;
}

export interface PricePoint {
  /** ISO date. */
  date: string;
  price: number;
}

/**
 * Behavioural signals consumed by the cart-abandonment agent. Every field is
 * optional-by-construction at the product level (`Product.signals?`) so the
 * catalog stays valid before any telemetry has been recorded.
 */
export interface ProductSignals {
  viewCount: number;
  searchCount: number;
  /** ISO timestamp of the most recent product-page view. */
  lastViewedAt?: string;
  /** ISO timestamp of cart add — the abandonment anchor. */
  addedToCartAt?: string;
  removedFromCartAt?: string;
  /** Milliseconds the item has sat in the cart without checkout. */
  cartDwellMs?: number;
  /** Feeds price-drop intervention. */
  priceHistory: PricePoint[];
  /** 0-1, written by the agent. */
  abandonmentScore?: number;
}

export interface SpecSection {
  section: string;
  items: { label: string; value: string }[];
}

export interface Review {
  id: string;
  reviewerName: string;
  rating: number;
  title: string;
  text: string;
  helpfulCount: number;
  /** ISO date. */
  date: string;
}

export interface RatingBreakdown {
  stars: 5 | 4 | 3 | 2 | 1;
  count: number;
}

export interface Seller {
  name: string;
  rating: number;
}

export interface Product {
  id: string;
  slug: string;
  title: string;
  brand: string;
  category: CategorySlug;
  subCategory: string;
  images: string[];
  price: Price;
  rating: Rating;
  badges: Badges;
  delivery: Delivery;
  offers: string[];
  emi?: Emi;
  stock: Stock;
  highlights: string[];
  signals?: ProductSignals;
  /**
   * PDP-only detail fields. Optional like `signals` — only populated for a
   * handful of products; the PDP renders a lighter page when absent instead
   * of showing placeholder/"coming soon" content.
   */
  specifications?: SpecSection[];
  reviews?: Review[];
  ratingDistribution?: RatingBreakdown[];
  seller?: Seller;
  description?: string;
}

export type SessionEventType =
  | "view"
  | "search"
  | "cart_add"
  | "cart_remove"
  | "checkout_start"
  | "abandon";

export interface SessionEvent {
  id: string;
  type: SessionEventType;
  productId?: string;
  query?: string;
  /** ISO timestamp. */
  timestamp: string;
}
