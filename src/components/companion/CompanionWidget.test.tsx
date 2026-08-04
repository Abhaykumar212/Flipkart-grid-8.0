import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthorizedIntervention } from "../../context/InterventionContext";
import { productById } from "../../data/products";
import { shoppingContext } from "../../lib/shoppingContext";
import { CompanionWidget } from "./CompanionWidget";

const interventionMocks = vi.hoisted(() => ({
  intervention: null as AuthorizedIntervention | null,
  explanation: null as Record<string, unknown> | null,
  shown: vi.fn(),
  click: vi.fn(),
  dismiss: vi.fn(),
}));

vi.mock("../../context/InterventionContext", () => ({
  useIntervention: () => interventionMocks,
}));

describe("CompanionWidget", () => {
  beforeEach(() => {
    shoppingContext.resetForTests();
    vi.clearAllMocks();
    interventionMocks.intervention = null;
    interventionMocks.explanation = null;
  });

  it("opens and answers a product question without a backend", () => {
    const product = productById.get("p-1001")!;
    shoppingContext.setCurrentProduct(product.id);
    render(<CompanionWidget />);

    fireEvent.click(screen.getByRole("button", { name: "Open shopping companion" }));
    expect(screen.getByText("No API key or network connection required.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Explain the price and offers" }));

    expect(screen.getByText(/₹71,999/)).toBeInTheDocument();
    expect(screen.getByRole("log")).toHaveTextContent("Flat ₹4,000 Instant Discount");
  });

  it("presents an authorized assistant intervention and preserves lifecycle callbacks", () => {
    interventionMocks.intervention = {
      decision_id: "D-202",
      type: "REVIEW_SUMMARY",
      channel: "ASSISTANT_PANEL",
      headline: "Review confidence",
      body: "A grounded summary may help.",
      reason: "You spent time reading reviews.",
      confidence: 0.84,
      cta_label: "Show summary",
    };
    interventionMocks.explanation = {
      observations: [{ statement: "You revisited customer reviews during this session." }],
    };
    render(<CompanionWidget />);

    expect(screen.getByRole("log")).toHaveTextContent("Review confidence");
    expect(interventionMocks.shown).toHaveBeenCalledWith("companion:ASSISTANT_PANEL");
    fireEvent.click(screen.getByRole("button", { name: "Show summary" }));
    expect(interventionMocks.click).toHaveBeenCalledOnce();
    expect(screen.getByText("Marked as helpful.")).toBeInTheDocument();
  });
});
