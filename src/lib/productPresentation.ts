import { categoryBySlug } from "../data/categories";
import type { Product, RatingBreakdown, Review, SpecSection } from "../types/product";

export function productVariantOptions(product: Product): string[] {
  if (product.category !== "fashion") return [];
  if (/shoes/i.test(product.subCategory)) return ["6", "7", "8", "9", "10"];
  if (/bags|backpacks/i.test(product.subCategory)) return [];
  return ["S", "M", "L", "XL"];
}

export function completeSpecifications(product: Product): SpecSection[] {
  if (product.specifications?.length) return product.specifications;
  const category = categoryBySlug.get(product.category);
  return [
    {
      section: "General",
      items: [
        { label: "Brand", value: product.brand },
        { label: "Category", value: category?.label ?? product.category },
        { label: "Product Type", value: product.subCategory },
        { label: "Model", value: product.slug.toUpperCase() },
      ],
    },
    {
      section: "Key Features",
      items: product.highlights.map((highlight, index) => ({
        label: `Feature ${index + 1}`,
        value: highlight,
      })),
    },
    {
      section: "Seller & Fulfilment",
      items: [
        { label: "Seller", value: product.seller?.name ?? "RetailNet" },
        { label: "Seller Rating", value: `${(product.seller?.rating ?? 4).toFixed(1)} / 5` },
        { label: "Availability", value: product.stock.inStock ? "In Stock" : "Out of Stock" },
        { label: "Delivery", value: product.delivery.free ? "Free delivery" : "Delivery charges apply" },
      ],
    },
  ];
}

export function completeDescription(product: Product): string {
  if (product.description) return product.description;
  const features = product.highlights.length
    ? ` Key features include ${product.highlights.join(", ")}.`
    : "";
  return `${product.title} from ${product.brand} is a highly rated ${product.subCategory.toLowerCase()} option built for everyday use.${features} It is sold with secure Flipkart-style fulfilment, transparent pricing, and delivery tracking.`;
}

export function completeRatingDistribution(product: Product): RatingBreakdown[] {
  if (product.ratingDistribution?.length) return product.ratingDistribution;
  const total = Math.max(product.rating.count, 1);
  const fiveShare = Math.min(0.82, Math.max(0.42, 0.42 + (product.rating.value - 3.5) * 0.35));
  const fourShare = Math.min(0.32, Math.max(0.12, 0.3 - (product.rating.value - 3.5) * 0.12));
  const threeShare = 0.1;
  const twoShare = 0.04;
  const counts = [
    Math.round(total * fiveShare),
    Math.round(total * fourShare),
    Math.round(total * threeShare),
    Math.round(total * twoShare),
  ];
  const used = counts.reduce((sum, count) => sum + count, 0);
  return [
    { stars: 5, count: counts[0] },
    { stars: 4, count: counts[1] },
    { stars: 3, count: counts[2] },
    { stars: 2, count: counts[3] },
    { stars: 1, count: Math.max(0, total - used) },
  ];
}

export function completeReviews(product: Product): Review[] {
  if (product.reviews?.length) return product.reviews;
  const highlight = product.highlights[0] ?? "The product matches the listing";
  return [
    {
      id: `${product.id}-review-1`,
      reviewerName: "Certified Buyer",
      rating: Math.max(1, Math.min(5, Math.round(product.rating.value))),
      title: product.rating.value >= 4.4 ? "Excellent choice" : "Good value for money",
      text: `${highlight}. The product arrived securely packed and has performed as expected in regular use.`,
      helpfulCount: Math.max(12, Math.round(product.rating.reviewCount * 0.04)),
      date: "2026-07-18",
    },
    {
      id: `${product.id}-review-2`,
      reviewerName: "Verified Customer",
      rating: Math.max(1, Math.min(5, Math.floor(product.rating.value))),
      title: "Worth considering",
      text: `Quality and finish are consistent with the description. Delivery was on time and the ${product.brand} packaging was intact.`,
      helpfulCount: Math.max(5, Math.round(product.rating.reviewCount * 0.018)),
      date: "2026-07-26",
    },
  ];
}
