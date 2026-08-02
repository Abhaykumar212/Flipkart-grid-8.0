import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { CartProvider } from "../../context/CartContext";
import { WishlistProvider } from "../../context/WishlistContext";
import { products } from "../../data/products";
import { ProductCard } from "./ProductCard";

describe("ProductCard", () => {
  it("renders a catalog product with its product link", () => {
    const product = products[0];

    render(
      <MemoryRouter>
        <CartProvider>
          <WishlistProvider>
            <ProductCard product={product} />
          </WishlistProvider>
        </CartProvider>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: product.title })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: `View ${product.title}` })).toHaveAttribute(
      "href",
      `/product/${product.slug}`,
    );
  });
});
