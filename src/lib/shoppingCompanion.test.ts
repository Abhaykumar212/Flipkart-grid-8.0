import { describe, expect, it } from "vitest";
import { productById } from "../data/products";
import { answerShoppingQuestion } from "./shoppingCompanion";

const iphone = productById.get("p-1001")!;
const iphoneBlack = productById.get("p-1002")!;
const galaxy = productById.get("p-1003")!;

describe("answerShoppingQuestion", () => {
  it("answers price and EMI questions only from listing values", () => {
    expect(answerShoppingQuestion("What is the best price and offer?", { product: iphone }))
      .toContain("₹71,999");
    expect(answerShoppingQuestion("Can I pay monthly with EMI?", { product: iphone }))
      .toContain("₹2,521 per month for 36 months");
  });

  it("returns balanced review evidence and exact aggregate counts", () => {
    const answer = answerShoppingQuestion("What do reviews say about battery?", { product: iphone });
    expect(answer).toContain("1,24,512 ratings");
    expect(answer).toContain("Positive feedback:");
    expect(answer).toContain("A concern raised:");
  });

  it("compares only the supplied products", () => {
    const answer = answerShoppingQuestion("Compare these phones", {
      product: iphone,
      comparisonProducts: [iphone, iphoneBlack, galaxy],
    });
    expect(answer).toContain(iphone.title);
    expect(answer).toContain(iphoneBlack.title);
    expect(answer).toContain(galaxy.title);
  });

  it("fails closed when no product listing can support the answer", () => {
    expect(answerShoppingQuestion("Does it have a ten year warranty?", { product: iphone }))
      .toContain("can’t verify");
    expect(answerShoppingQuestion("What is the battery like?", {}))
      .toContain("Open a product first");
  });
});
