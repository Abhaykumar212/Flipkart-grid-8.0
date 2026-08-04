import { describe, expect, it, vi } from "vitest";
import { findComparisonCandidates, ShoppingContextStore } from "./shoppingContext";

describe("ShoppingContextStore", () => {
  it("keeps bounded, deduplicated browsing context and fresh visit counts", () => {
    vi.spyOn(Date, "now").mockReturnValue(100);
    const store = new ShoppingContextStore();
    store.setCurrentProduct("p-1");
    store.recordVisit({ productId: "p-1", title: "One", category: "mobiles", price: 10_000 });
    store.recordVisit({ productId: "p-1", title: "One", category: "mobiles", price: 10_000 });
    store.recordSearch("phone");
    store.recordSearch("phone");

    expect(store.getSnapshot().visitHistory).toHaveLength(1);
    expect(store.getSnapshot().visitHistory[0].visitCount).toBe(2);
    expect(store.getSnapshot().searchHistory).toEqual(["phone"]);
    vi.restoreAllMocks();
  });

  it("finds only same-category, similarly priced comparison clusters", () => {
    const visits = [
      { productId: "a", title: "A", category: "mobiles", price: 10_000, lastVisitedAt: 3, visitCount: 1 },
      { productId: "b", title: "B", category: "mobiles", price: 12_000, lastVisitedAt: 2, visitCount: 1 },
      { productId: "c", title: "C", category: "mobiles", price: 15_000, lastVisitedAt: 1, visitCount: 1 },
    ];
    expect(findComparisonCandidates(visits)?.map((item) => item.productId)).toEqual(["a", "b", "c"]);
    expect(findComparisonCandidates([{ ...visits[0] }, { ...visits[1] }])).toBeNull();
    expect(findComparisonCandidates([visits[0], visits[1], { ...visits[2], price: 30_000 }])).toBeNull();
  });
});
