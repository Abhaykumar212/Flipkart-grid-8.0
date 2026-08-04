import { describe, expect, it } from "vitest";
import { customerExplanation } from "./interventionPresentation";

describe("customerExplanation", () => {
  it("selects safe prose without leaking raw feature metadata", () => {
    const reasons = customerExplanation({
      observations: [{ feature: "rev_dwell_seconds", shap: 0.42, statement: "You spent time reading customer reviews." }],
      inference: { root_cause: "PRODUCT_QUALITY_UNCERTAINTY", statement: "Product quality questions appear unresolved." },
      versions: { risk: "secret-model-version" },
    }, "Fallback");
    expect(reasons).toEqual([
      "You spent time reading customer reviews.",
      "Product quality questions appear unresolved.",
    ]);
    expect(reasons.join(" ")).not.toContain("rev_dwell_seconds");
    expect(reasons.join(" ")).not.toContain("secret-model-version");
  });

  it("uses the governed intervention reason when structured prose is unavailable", () => {
    expect(customerExplanation(null, "Delivery timing was checked repeatedly."))
      .toEqual(["Delivery timing was checked repeatedly."]);
  });
});
