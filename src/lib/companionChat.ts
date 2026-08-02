/**
 * Client for the companion's reactive Q&A endpoint. Context-stuffed, not
 * retrieved — see backend/agents/companion_chat.py for why: the per-product
 * corpus (a handful of reviews, a short spec sheet) is small enough that
 * sending it all beats retrieving a subset of it.
 */

import type { Product } from "../types/product";
import {
  getDescription,
  getRatingDistribution,
  getReviews,
  getSeller,
  getSpecifications,
} from "./productDetails";
import { SESSION_ID } from "./tracker";

export interface ChatMessagePayload {
  role: "user" | "assistant";
  content: string;
}

export interface ProductContextPayload {
  title: string;
  brand: string;
  category: string;
  mrp: number;
  selling_price: number;
  description: string;
  highlights: string[];
  specifications: Array<{ label: string; value: string }>;
  delivery_free: boolean;
  estimated_delivery_days: number;
  emi_monthly: number | null;
  emi_months: number | null;
  offers: string[];
  seller_name: string;
  seller_rating: number;
  rating_value: number;
  rating_count: number;
  rating_distribution: Array<{ stars: number; count: number }>;
  in_stock: boolean;
  quantity_left: number;
  reviews: Array<{ rating: number; title: string; text: string }>;
}

export interface CompanionChatResponse {
  status: "success" | "rate_limited" | "not_configured" | "error";
  reply: string | null;
  model_used: string | null;
  latency_ms: number;
  message: string | null;
}

const API_BASE = "http://localhost:8000";
const COMPANION_CHAT_URL = `${API_BASE}/api/companion-chat`;

/** Flattens the PDP's sectioned spec sheet into the flat label/value list the agent expects. */
export function buildProductContext(product: Product): ProductContextPayload {
  const specifications = getSpecifications(product).flatMap((section) =>
    section.items.map((item) => ({ label: item.label, value: item.value })),
  );
  const seller = getSeller(product);
  const reviews = getReviews(product).map((review) => ({
    rating: review.rating,
    title: review.title,
    text: review.text,
  }));

  return {
    title: product.title,
    brand: product.brand,
    category: product.category,
    mrp: product.price.mrp,
    selling_price: product.price.sellingPrice,
    description: getDescription(product),
    highlights: product.highlights,
    specifications,
    delivery_free: product.delivery.free,
    estimated_delivery_days: product.delivery.estimatedDays,
    emi_monthly: product.emi?.monthly ?? null,
    emi_months: product.emi?.months ?? null,
    offers: product.offers,
    seller_name: seller.name,
    seller_rating: seller.rating,
    rating_value: product.rating.value,
    rating_count: product.rating.count,
    rating_distribution: getRatingDistribution(product).map((entry) => ({
      stars: entry.stars,
      count: entry.count,
    })),
    in_stock: product.stock.inStock,
    quantity_left: product.stock.quantityLeft,
    reviews,
  };
}

export async function sendCompanionChatMessage(
  productContext: ProductContextPayload | null,
  messages: ChatMessagePayload[],
  comparisonProducts: ProductContextPayload[] = [],
  searchHistory: string[] = [],
): Promise<CompanionChatResponse> {
  const response = await fetch(COMPANION_CHAT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: SESSION_ID,
      product_context: productContext,
      comparison_products: comparisonProducts,
      search_history: searchHistory,
      messages,
    }),
  });

  if (!response.ok) {
    throw new Error(`Companion chat API returned ${response.status}`);
  }
  return response.json();
}
