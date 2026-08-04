import { describe, expect, it } from "vitest";
import { productById } from "../data/products";
import {
  categoryDiscoveries,
  comparableProducts,
  recentlyViewedProducts,
  similarProducts,
} from "./productRecommendations";

const current = productById.get("p-1001")!;

describe("product recommendations", () => {
  it("keeps comparisons in the same subcategory and price band", () => {
    const candidates = comparableProducts(current);
    expect(candidates.length).toBeGreaterThan(0);
    expect(candidates.every((product) => product.subCategory === current.subCategory)).toBe(true);
    expect(candidates.every((product) => (
      product.price.sellingPrice >= current.price.sellingPrice * 0.6
      && product.price.sellingPrice <= current.price.sellingPrice * 1.4
    ))).toBe(true);
  });

  it("keeps recommendation reasons distinct and excludes the current product", () => {
    expect(similarProducts(current).every((product) => (
      product.id !== current.id && product.subCategory === current.subCategory
    ))).toBe(true);
    expect(categoryDiscoveries(current).every((product) => (
      product.id !== current.id
      && product.category === current.category
      && product.subCategory !== current.subCategory
    ))).toBe(true);
  });

  it("replays recently viewed products in visit order", () => {
    const history = ["p-1003", "p-1002", current.id].map((productId, index) => ({
      productId,
      title: productId,
      category: "mobiles",
      price: 50_000,
      lastVisitedAt: 3 - index,
      visitCount: 1,
    }));
    expect(recentlyViewedProducts(history, current.id).map((product) => product.id))
      .toEqual(["p-1003", "p-1002"]);
  });
});
