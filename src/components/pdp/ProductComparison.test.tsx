import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { productById } from "../../data/products";
import { comparableProducts } from "../../lib/productRecommendations";
import { ProductComparison } from "./ProductComparison";

const emit = vi.fn();
vi.mock("../../context/SessionContext", () => ({ useSession: () => ({ emit }) }));

describe("ProductComparison", () => {
  beforeEach(() => emit.mockClear());

  it("reveals a real table and emits the canonical comparison event once", () => {
    const current = productById.get("p-1001")!;
    const alternatives = comparableProducts(current);
    render(
      <MemoryRouter>
        <ProductComparison current={current} alternatives={alternatives} />
      </MemoryRouter>,
    );

    const toggle = screen.getByRole("button", { name: /Compare \d+ items/ });
    fireEvent.click(toggle);
    expect(screen.getByTestId("product-comparison-table")).toBeInTheDocument();
    expect(emit).toHaveBeenCalledWith("PRODUCT_COMPARED", {
      productId: current.id,
      metadata: { compared_with: alternatives.map((product) => product.id) },
    });
    fireEvent.click(screen.getByRole("button", { name: "Hide comparison" }));
    expect(emit).toHaveBeenCalledOnce();
  });
});
