import { useNavigate } from "react-router-dom";
import { ShoppingCart } from "lucide-react";
import { useCart } from "../context/CartContext";
import { computeCartTotals } from "../lib/cartTotals";
import { productById, products } from "../data/products";
import { Button } from "../components/ui/Button";
import { CartLineItem } from "../components/cart/CartLineItem";
import { PriceSummary } from "../components/cart/PriceSummary";
import { ProductRail } from "../components/home/ProductRail";

export default function CartPage() {
  const { items } = useCart();
  const navigate = useNavigate();

  // Resolve cart lines against the catalog, dropping any id that no longer exists.
  const lines = items.flatMap((item) => {
    const product = productById.get(item.productId);
    return product ? [{ product, quantity: item.quantity }] : [];
  });

  const totals = computeCartTotals(items);

  const inCart = new Set(items.map((i) => i.productId));
  const recommendations = products.filter((p) => !inCart.has(p.id)).slice(0, 12);

  if (lines.length === 0) {
    return (
      <div
        className="flex flex-col items-center gap-3 bg-white px-6 py-20 text-center"
        data-testid="cart-empty"
      >
        <ShoppingCart className="h-16 w-16 text-fk-border" strokeWidth={1.5} />
        <h1 className="text-fk-lg font-medium text-fk-ink">Your cart is empty!</h1>
        <p className="text-fk-base text-fk-muted">Add items to it now.</p>
        <Button variant="primary" className="mt-2" onClick={() => navigate("/")}>
          Shop now
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[65fr_35fr]">
        <div className="flex flex-col gap-3">
          {lines.map(({ product, quantity }) => (
            <CartLineItem key={product.id} product={product} quantity={quantity} />
          ))}
        </div>

        <PriceSummary
          totals={totals}
          action={{
            label: "Place Order",
            testId: "place-order-button",
            onClick: () => navigate("/checkout"),
          }}
        />
      </div>

      {recommendations.length > 0 && (
        <ProductRail title="You might also like" products={recommendations} />
      )}
    </div>
  );
}
