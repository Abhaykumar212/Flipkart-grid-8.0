import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BadgePercent, ShieldCheck, ShoppingCart, X } from "lucide-react";
import { useCart } from "../context/CartContext";
import {
  computeCartTotals,
  FREE_DELIVERY_THRESHOLD,
  PROMO_CODES,
} from "../lib/cartTotals";
import { productById, products } from "../data/products";
import { formatINR } from "../lib/format";
import { Button } from "../components/ui/Button";
import { CartLineItem } from "../components/cart/CartLineItem";
import { PriceSummary } from "../components/cart/PriceSummary";
import { ProductRail } from "../components/home/ProductRail";
import { useSession } from "../context/SessionContext";
import { InterventionRenderer } from "../components/intervention/InterventionRenderer";

export default function CartPage() {
  const { items, promoCode, applyPromo, removePromo } = useCart();
  const navigate = useNavigate();
  const { emit } = useSession();
  const cartViewRecorded = useRef(false);
  const [code, setCode] = useState("");
  const [promoMessage, setPromoMessage] = useState("");

  const lines = items.flatMap((item) => {
    const product = productById.get(item.productId);
    return product ? [{ product, quantity: item.quantity, variant: item.variant }] : [];
  });
  const totals = computeCartTotals(items, promoCode);
  const inCart = new Set(items.map((item) => item.productId));
  const recommendations = products.filter((product) => !inCart.has(product.id)).slice(0, 12);

  useEffect(() => {
    if (cartViewRecorded.current) return;
    cartViewRecorded.current = true;
    emit("CART_VIEWED", {
      metadata: { cart_value: totals.totalSellingPrice, item_count: totals.itemCount },
    });
  }, [emit, totals.itemCount, totals.totalSellingPrice]);

  const submitPromo = (event: React.FormEvent) => {
    event.preventDefault();
    const normalized = code.trim().toUpperCase();
    if (!(normalized in PROMO_CODES)) {
      emit("COUPON_SEARCHED", { metadata: { code: normalized || null, applied: false } });
      setPromoMessage("That coupon code is not valid.");
      return;
    }
    if (normalized === "FLIPKART200" && totals.totalSellingPrice < 2000) {
      emit("COUPON_SEARCHED", { metadata: { code: normalized, applied: false } });
      setPromoMessage("FLIPKART200 requires a minimum cart value of ₹2,000.");
      return;
    }
    emit("COUPON_SEARCHED", { metadata: { code: normalized, applied: true } });
    applyPromo(normalized);
    setCode("");
    setPromoMessage("Coupon applied successfully.");
  };

  if (lines.length === 0) {
    return (
      <div className="flex min-h-[480px] flex-col items-center justify-center gap-3 bg-white px-6 py-20 text-center" data-testid="cart-empty">
        <ShoppingCart className="h-16 w-16 text-fk-border" strokeWidth={1.5} />
        <h1 className="text-fk-xl font-medium text-fk-ink">Your cart is empty</h1>
        <p className="text-fk-base text-fk-muted">Add items from the complete catalog to see them here.</p>
        <Button variant="primary" className="mt-2" onClick={() => navigate("/products")}>Shop now</Button>
      </div>
    );
  }

  const remainingForFreeDelivery = Math.max(0, FREE_DELIVERY_THRESHOLD - totals.totalSellingPrice);

  return (
    <div className="flex flex-col gap-3 pb-[calc(76px+env(safe-area-inset-bottom))] lg:pb-0">
      <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[65fr_35fr]">
        <div className="flex flex-col gap-3">
          <header className="flex items-center justify-between bg-white px-4 py-4 sm:px-6">
            <h1 className="text-xl font-medium text-fk-ink">My Cart ({totals.itemCount})</h1>
            <Link to="/products" className="min-h-11 content-center text-fk-md font-medium text-fk-blue">Continue shopping</Link>
          </header>

          <InterventionRenderer surface="cart" />

          {remainingForFreeDelivery > 0 ? (
            <div className="bg-white px-4 py-3 text-fk-base text-fk-ink sm:px-6">
              Add <strong>{formatINR(remainingForFreeDelivery)}</strong> more for free delivery.
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-fk-bg"><div className="h-full bg-fk-green" style={{ width: `${Math.min(100, (totals.totalSellingPrice / FREE_DELIVERY_THRESHOLD) * 100)}%` }} /></div>
            </div>
          ) : (
            <div className="flex items-center gap-2 bg-white px-4 py-3 text-fk-base font-medium text-fk-green sm:px-6"><ShieldCheck className="h-5 w-5" />Your order qualifies for free delivery</div>
          )}

          {lines.map(({ product, quantity, variant }) => (
            <CartLineItem key={`${product.id}:${variant ?? "default"}`} product={product} quantity={quantity} variant={variant} />
          ))}

          <section className="bg-white p-4 sm:p-6" aria-labelledby="coupon-title">
            <div className="flex items-center gap-2"><BadgePercent className="h-5 w-5 text-fk-blue" /><h2 id="coupon-title" className="text-fk-md font-medium text-fk-ink">Coupons</h2></div>
            {promoCode ? (
              <div className="mt-3 flex items-center justify-between rounded-[2px] border border-fk-green bg-green-50 px-3 py-3 text-fk-base">
                <span><strong>{promoCode}</strong> · {PROMO_CODES[promoCode as keyof typeof PROMO_CODES]}</span>
                <button onClick={() => { removePromo(); setPromoMessage("Coupon removed."); }} className="flex h-11 w-11 items-center justify-center text-fk-muted" aria-label="Remove coupon"><X className="h-4 w-4" /></button>
              </div>
            ) : (
              <form onSubmit={submitPromo} className="mt-3 flex max-w-lg flex-col gap-2 sm:flex-row">
                <input name="coupon" autoComplete="off" spellCheck={false} value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} placeholder="Enter coupon code" aria-label="Coupon code" className="h-12 flex-1 rounded-[2px] border border-fk-border px-3 text-base uppercase focus:border-fk-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-fk-blue" />
                <Button type="submit" variant="outline" disabled={!code.trim()} className="min-h-12">Apply</Button>
              </form>
            )}
            <p className={`mt-2 min-h-5 text-fk-sm ${promoMessage.includes("success") || promoMessage.includes("removed") ? "text-fk-green" : "text-fk-flame"}`} aria-live="polite">{promoMessage}</p>
            {!promoCode && <p className="text-fk-sm text-fk-muted">Try WELCOME10 or FLIPKART200.</p>}
          </section>
        </div>

        <PriceSummary totals={totals} action={{ label: "Proceed to Checkout", testId: "place-order-button", onClick: () => navigate("/checkout") }} />
      </div>

      {recommendations.length > 0 && <ProductRail title="You might also like" products={recommendations} />}

      <div className="fixed inset-x-0 bottom-0 z-40 flex items-center justify-between gap-3 border-t border-fk-border bg-white px-4 py-3 shadow-[0_-2px_8px_rgba(0,0,0,0.12)] [padding-bottom:calc(0.75rem+env(safe-area-inset-bottom))] lg:hidden">
        <span className="text-fk-lg font-bold text-fk-ink">{formatINR(totals.totalAmount)}</span>
        <Button variant="buy" onClick={() => navigate("/checkout")} className="min-h-12 flex-1">Checkout</Button>
      </div>
    </div>
  );
}
