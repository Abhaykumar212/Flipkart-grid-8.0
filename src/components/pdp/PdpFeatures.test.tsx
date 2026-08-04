import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { productById } from "../../data/products";
import { shoppingContext } from "../../lib/shoppingContext";
import { EMICalculator } from "./EMICalculator";
import { ProductQuestions } from "./ProductQuestions";
import { StockStatus } from "./StockStatus";

const product = productById.get("p-1001")!;

describe("PDP customer features", () => {
  beforeEach(() => shoppingContext.resetForTests());

  it("labels computed EMI values as estimates", () => {
    render(<EMICalculator sellingPrice={product.price.sellingPrice} emi={product.emi} />);
    expect(screen.getByText(/₹2,521 × 36 months/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Compare monthly estimates" }));
    expect(screen.getAllByText("principal-only estimate").length).toBeGreaterThan(0);
    expect(screen.getByText(/final charges are confirmed at checkout/i)).toBeInTheDocument();
  });

  it("sends a submitted product question to the companion", () => {
    render(<ProductQuestions product={product} />);
    fireEvent.change(screen.getByLabelText(`Question about ${product.title}`), {
      target: { value: "What do reviewers say about battery?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask companion" }));
    expect(shoppingContext.getSnapshot().companionRequest?.prompt)
      .toBe("What do reviewers say about battery?");
    expect(screen.getByRole("status")).toHaveTextContent("grounded answer is open");
  });

  it("shows stock facts without a decorative notification action", () => {
    const { rerender } = render(<StockStatus stock={{ inStock: true, quantityLeft: 3 }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Only 3 left");
    rerender(<StockStatus stock={{ inStock: false, quantityLeft: 0 }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Currently unavailable");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
