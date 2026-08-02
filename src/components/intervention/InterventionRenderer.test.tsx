import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthorizedIntervention } from "../../context/InterventionContext";
import { InterventionRenderer } from "./InterventionRenderer";

const mocks = vi.hoisted(() => ({
  shown: vi.fn(),
  click: vi.fn(),
  dismiss: vi.fn(),
  intervention: null as AuthorizedIntervention | null,
}));

vi.mock("../../context/InterventionContext", () => ({
  useIntervention: () => ({
    intervention: mocks.intervention,
    explanation: null,
    shown: mocks.shown,
    click: mocks.click,
    dismiss: mocks.dismiss,
  }),
}));

describe("InterventionRenderer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.intervention = null;
  });

  it("renders only a backend-authorized decision and emits lifecycle actions", () => {
    mocks.intervention = {
      decision_id: "D-101",
      type: "REVIEW_SUMMARY",
      channel: "INLINE_CARD",
      headline: "What shoppers are saying",
      body: "A grounded summary is ready.",
      reason: "Review activity",
      confidence: 0.82,
      cta_label: "See highlights",
    };
    render(<InterventionRenderer surface="cart" />);

    expect(screen.getByTestId("intervention-inline-card")).toBeInTheDocument();
    expect(mocks.shown).toHaveBeenCalledWith("cart:INLINE_CARD");
    fireEvent.click(screen.getByRole("button", { name: "See highlights" }));
    fireEvent.click(screen.getByRole("button", { name: "Dismiss recommendation" }));
    expect(mocks.click).toHaveBeenCalledOnce();
    expect(mocks.dismiss).toHaveBeenCalledOnce();
  });

  it("renders nothing when the backend decision id is missing", () => {
    mocks.intervention = {
      type: "REVIEW_SUMMARY",
      channel: "INLINE_CARD",
      reason: "Review activity",
      confidence: 0.82,
    } as AuthorizedIntervention;
    const { container } = render(<InterventionRenderer surface="cart" />);
    expect(container).toBeEmptyDOMElement();
    expect(mocks.shown).not.toHaveBeenCalled();
  });
});
