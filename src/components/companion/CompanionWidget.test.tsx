import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { productById } from "../../data/products";
import { shoppingContext } from "../../lib/shoppingContext";
import { CompanionWidget } from "./CompanionWidget";

describe("CompanionWidget", () => {
  beforeEach(() => shoppingContext.resetForTests());

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
});
