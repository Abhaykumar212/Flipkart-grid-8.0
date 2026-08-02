import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { CartProvider } from "../../context/CartContext";
import { WishlistProvider } from "../../context/WishlistContext";
import { products } from "../../data/products";
import { ProductCard } from "./ProductCard";
import { SessionProvider } from "../../context/SessionContext";

describe("ProductCard", () => {
  it("renders a catalog product with its product link", () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(
      JSON.stringify({ session_id: "test" }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    ));
    const product = products[0];

    render(
      <MemoryRouter>
        <SessionProvider>
          <CartProvider>
            <WishlistProvider>
              <ProductCard product={product} />
            </WishlistProvider>
          </CartProvider>
        </SessionProvider>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: product.title })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: `View ${product.title}` })).toHaveAttribute(
      "href",
      `/product/${product.slug}`,
    );
  });
});
