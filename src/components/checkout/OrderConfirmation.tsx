import { useEffect, useRef, useState } from "react";
import { CircleCheck, Copy, Mail, PackageCheck, Printer, Truck } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "../ui/Button";
import { productById } from "../../data/products";
import { paymentMethodLabel } from "../../data/checkout";
import { formatINR } from "../../lib/format";
import type { PlacedOrder } from "../../types/checkout";
import { useSession } from "../../context/SessionContext";

export function OrderConfirmation({ order }: { order: PlacedOrder }) {
  const { emit } = useSession();
  const recordedOrder = useRef<string | null>(null);
  const [copied, setCopied] = useState(false);
  const lines = order.items.flatMap((item) => {
    const product = productById.get(item.productId);
    return product ? [{ ...item, product }] : [];
  });

  useEffect(() => {
    if (recordedOrder.current === order.id) return;
    recordedOrder.current = order.id;
    emit("ORDER_COMPLETED", {
      metadata: {
        order_id: order.id,
        order_value: order.totals.totalAmount,
        payment_method: order.paymentMethod.toUpperCase(),
      },
    });
  }, [emit, order]);

  const copyOrderId = async () => {
    await navigator.clipboard.writeText(order.id);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <main className="mx-auto w-full max-w-4xl space-y-3" data-testid="order-confirmation" aria-live="polite">
      <section className="bg-white px-5 py-10 text-center sm:px-8">
        <CircleCheck className="mx-auto h-16 w-16 text-fk-green" strokeWidth={1.5} />
        <h1 className="mt-3 text-2xl font-medium text-fk-ink">Order confirmed</h1>
        <p className="mt-2 text-fk-base text-fk-muted">A confirmation summary has been prepared for {order.address.email}.</p>
        <div className="mx-auto mt-5 inline-flex items-center gap-2 rounded-[2px] bg-fk-bg px-4 py-3">
          <span className="text-fk-sm text-fk-muted">Order ID</span>
          <strong className="select-all text-fk-md text-fk-ink" data-testid="order-id">{order.id}</strong>
          <button onClick={copyOrderId} className="flex h-11 w-11 items-center justify-center text-fk-blue" aria-label="Copy order ID"><Copy className="h-4 w-4" /></button>
        </div>
        <p className="min-h-5 text-fk-sm text-fk-green" aria-live="polite">{copied ? "Order ID copied" : ""}</p>
      </section>

      <section className="bg-white p-5 sm:p-6" aria-labelledby="ordered-items-title">
        <h2 id="ordered-items-title" className="text-fk-xl font-medium text-fk-ink">Items in this order</h2>
        <div className="mt-4 divide-y divide-fk-border">
          {lines.map(({ product, quantity, variant }) => (
            <article key={`${product.id}:${variant ?? "default"}`} className="flex gap-4 py-4 first:pt-0">
              <img src={product.images[0]} alt={product.title} loading="lazy" width="80" height="80" className="h-20 w-20 shrink-0 object-contain" />
              <div className="min-w-0 flex-1"><h3 className="text-fk-md font-medium text-fk-ink">{product.title}</h3>{variant && <p className="mt-1 text-fk-sm text-fk-muted">{variant}</p>}<p className="mt-1 text-fk-sm text-fk-muted">Qty: {quantity}</p></div>
              <strong className="shrink-0 text-fk-md text-fk-ink">{formatINR(product.price.sellingPrice * quantity)}</strong>
            </article>
          ))}
        </div>
      </section>

      <div className="grid gap-3 md:grid-cols-2">
        <section className="bg-white p-5 sm:p-6" aria-labelledby="delivery-details-title">
          <h2 id="delivery-details-title" className="text-fk-xl font-medium text-fk-ink">Delivery details</h2>
          <address className="mt-3 text-fk-base not-italic leading-6 text-fk-ink"><strong>{order.address.name}</strong><br />{order.address.addressLine}<br />{order.address.city}, {order.address.state} — {order.address.pincode}<br />{order.address.phone}</address>
          <div className="mt-4 border-t border-fk-border pt-3 text-fk-base"><strong>{order.shippingMethod.label}</strong><p className="text-fk-muted">Estimated delivery by <span className="font-medium text-fk-green">{order.deliveryDate}</span></p></div>
        </section>

        <section className="bg-white p-5 sm:p-6" aria-labelledby="payment-summary-title">
          <h2 id="payment-summary-title" className="text-fk-xl font-medium text-fk-ink">Payment summary</h2>
          <dl className="mt-3 space-y-3 text-fk-base">
            <div className="flex justify-between"><dt>Items</dt><dd>{formatINR(order.totals.totalSellingPrice)}</dd></div>
            {order.totals.promoDiscount > 0 && <div className="flex justify-between text-fk-green"><dt>Coupon</dt><dd>− {formatINR(order.totals.promoDiscount)}</dd></div>}
            <div className="flex justify-between"><dt>Delivery</dt><dd>{order.totals.deliveryCharge ? formatINR(order.totals.deliveryCharge) : "Free"}</dd></div>
            <div className="flex justify-between border-t border-dashed border-fk-border pt-3 text-fk-lg font-bold"><dt>Total</dt><dd>{formatINR(order.totals.totalAmount)}</dd></div>
          </dl>
          <p className="mt-4 text-fk-sm text-fk-muted">Payment method: {paymentMethodLabel.get(order.paymentMethod)}</p>
        </section>
      </div>

      <section className="bg-white p-5 sm:p-6" aria-labelledby="next-steps-title">
        <h2 id="next-steps-title" className="text-fk-xl font-medium text-fk-ink">What happens next</h2>
        <ol className="mt-5 grid gap-5 sm:grid-cols-3">
          <li className="flex gap-3"><PackageCheck className="h-6 w-6 shrink-0 text-fk-blue" /><span><strong className="block text-fk-md">Order processing</strong><span className="text-fk-sm text-fk-muted">The seller prepares and verifies your items.</span></span></li>
          <li className="flex gap-3"><Mail className="h-6 w-6 shrink-0 text-fk-blue" /><span><strong className="block text-fk-md">Shipment update</strong><span className="text-fk-sm text-fk-muted">Tracking information will be sent to your email.</span></span></li>
          <li className="flex gap-3"><Truck className="h-6 w-6 shrink-0 text-fk-blue" /><span><strong className="block text-fk-md">Delivery</strong><span className="text-fk-sm text-fk-muted">Your order is expected by {order.deliveryDate}.</span></span></li>
        </ol>
      </section>

      <div className="flex flex-col gap-3 bg-white p-5 sm:flex-row sm:justify-center">
        <Link to="/products" className="inline-flex min-h-12 items-center justify-center rounded-[2px] bg-fk-blue px-7 text-fk-md font-medium uppercase text-white hover:bg-fk-blue-dark">Continue Shopping</Link>
        <Button variant="outline" className="min-h-12" onClick={() => window.print()}><Printer className="h-4 w-4" /> Print receipt</Button>
      </div>
    </main>
  );
}
