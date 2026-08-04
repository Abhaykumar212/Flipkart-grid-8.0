import type { Product, Review } from "../types/product";
import { formatINR } from "./format";
import {
  getDescription,
  getRatingDistribution,
  getReviews,
  getSeller,
  getSpecifications,
} from "./productDetails";

export interface CompanionQuestionContext {
  product?: Product;
  comparisonProducts?: Product[];
  searchHistory?: string[];
}

const STOP_WORDS = new Set([
  "about", "are", "can", "does", "for", "from", "have", "how", "is", "it", "me",
  "of", "on", "tell", "that", "the", "this", "what", "which", "with", "you",
]);

function sentence(text: string): string {
  const trimmed = text.trim();
  return /[.!?]$/.test(trimmed) ? trimmed : `${trimmed}.`;
}

function reviewAnswer(product: Product, question: string): string {
  const reviews = getReviews(product);
  const distribution = getRatingDistribution(product);
  const total = distribution.reduce((sum, item) => sum + item.count, 0);
  const positive = distribution
    .filter((item) => item.stars >= 4)
    .reduce((sum, item) => sum + item.count, 0);
  const positiveShare = total > 0 ? Math.round((positive / total) * 100) : 0;
  const terms = question
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((term) => term.length >= 4 && !STOP_WORDS.has(term));
  const relevant = reviews.filter((review) => terms.some((term) => (
    `${review.title} ${review.text}`.toLowerCase().includes(term)
  )));
  const sample = relevant.length > 0 ? relevant : reviews;
  const praise = sample.find((review) => review.rating >= 4);
  const concern = sample.find((review) => (
    review.rating <= 3 || /\b(but|however|although|could be|wish|drains?|downside)\b/i.test(review.text)
  ));
  const concernText = concern?.text.match(/\b(?:but|however|although)\b[\s,]*(.+)$/i)?.[1]
    ?? concern?.text;
  const observations = [
    praise ? `Positive feedback: ${sentence(praise.text)}` : "",
    concernText ? `A concern raised: ${sentence(concernText)}` : "",
  ].filter(Boolean).join(" ");

  return `${product.rating.value.toFixed(1)}/5 from ${total.toLocaleString("en-IN")} ratings; ${positiveShare}% are 4★ or 5★. ${observations || "The listing has no written review sample for that detail."}`;
}

function comparisonAnswer(products: Product[]): string {
  if (products.length < 2) return "Open a few comparable products and I can line them up for you.";
  const rows = products.slice(0, 4).map((product) => (
    `${product.title}: ${formatINR(product.price.sellingPrice)}, ${product.rating.value.toFixed(1)}★, ${product.highlights.slice(0, 2).join("; ")}`
  ));
  return `Here’s the side-by-side from the listings you viewed:\n${rows.join("\n")}`;
}

function specificationAnswer(product: Product, question: string): string | null {
  const terms = question
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((term) => term.length >= 3 && !STOP_WORDS.has(term));
  const matches = getSpecifications(product)
    .flatMap((section) => section.items)
    .filter((item) => terms.some((term) => (
      `${item.label} ${item.value}`.toLowerCase().includes(term)
    )))
    .slice(0, 5);
  return matches.length > 0
    ? matches.map((item) => `${item.label}: ${item.value}`).join(" · ")
    : null;
}

export function answerShoppingQuestion(
  question: string,
  context: CompanionQuestionContext,
): string {
  const normalized = question.trim().toLowerCase();
  const product = context.product;
  const comparisons = context.comparisonProducts ?? [];

  if (/what.*search|search history|looking for/.test(normalized)) {
    const searches = context.searchHistory ?? [];
    return searches.length > 0
      ? `This session you searched for ${searches.slice(0, 5).map((item) => `“${item}”`).join(", ")}.`
      : "You haven’t searched for anything in this session yet.";
  }

  if (/compare|difference|versus|\bvs\b|side.by.side/.test(normalized)) {
    return comparisonAnswer(comparisons.length > 0 ? comparisons : product ? [product] : []);
  }

  if (!product) {
    return /^(hi|hello|hey)\b/.test(normalized)
      ? "Hi! Open a product and I can explain its price, offers, delivery, specifications, and review signals."
      : "Open a product first so I can answer from its actual listing instead of guessing.";
  }

  if (/price|discount|deal|offer|coupon|cashback|exchange/.test(normalized)) {
    const discount = product.price.mrp > product.price.sellingPrice
      ? Math.round((1 - product.price.sellingPrice / product.price.mrp) * 100)
      : 0;
    const offers = product.offers.length > 0
      ? ` Listed offers: ${product.offers.join("; ")}.`
      : " No additional offer is listed.";
    return `${product.title} is ${formatINR(product.price.sellingPrice)}${discount > 0 ? `, ${discount}% below its ${formatINR(product.price.mrp)} MRP` : ""}.${offers}`;
  }

  if (/emi|installment|monthly|finance/.test(normalized)) {
    return product.emi
      ? `The listing shows EMI at ${formatINR(product.emi.monthly)} per month for ${product.emi.months} months. Final bank eligibility and charges are confirmed at checkout.`
      : "This listing does not specify an EMI plan, so I can’t confirm one.";
  }

  if (/deliver|shipping|arrive|pincode|stock|available/.test(normalized)) {
    if (!product.stock.inStock) return "The listing currently marks this product out of stock.";
    return `${product.delivery.free ? "Free delivery" : "Delivery charges apply"}; the listed estimate is ${product.delivery.estimatedDays} day${product.delivery.estimatedDays === 1 ? "" : "s"}. ${product.stock.quantityLeft > 0 ? `${product.stock.quantityLeft} units are shown in stock.` : "It is shown as in stock."}`;
  }

  if (/review|rating|worth|quality|battery|camera|durab|comfort|fit|sound/.test(normalized)) {
    return reviewAnswer(product, normalized);
  }

  if (/seller|sold by/.test(normalized)) {
    const seller = getSeller(product);
    return `The listing names ${seller.name} as the seller with a ${seller.rating.toFixed(1)}★ seller rating.`;
  }

  if (/spec|feature|processor|display|material|capacity|warranty|model|size/.test(normalized)) {
    const matched = specificationAnswer(product, normalized);
    return matched ?? "That detail is not included in this product’s listing, so I can’t verify it.";
  }

  if (/describe|summary|overview|tell me/.test(normalized)) {
    return `${sentence(getDescription(product))} It is listed at ${formatINR(product.price.sellingPrice)} with a ${product.rating.value.toFixed(1)}★ rating.`;
  }

  return `I can answer from this listing about price and offers, EMI, delivery, stock, seller, specifications, and reviews. I don’t have verified information beyond those details.`;
}

export function reviewTopics(reviews: Review[]): string[] {
  const candidates = ["battery", "camera", "display", "comfort", "fit", "quality", "sound"];
  return candidates.filter((topic) => reviews.some((review) => (
    `${review.title} ${review.text}`.toLowerCase().includes(topic)
  ))).slice(0, 3);
}
