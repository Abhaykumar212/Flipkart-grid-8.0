import { useState } from "react";
import { Navigate } from "react-router-dom";
import { LockKeyhole } from "lucide-react";
import { useCart } from "../context/CartContext";
import { computeCartTotals } from "../lib/cartTotals";
import { productById } from "../data/products";
import { formatDeliveryDate, formatINR } from "../lib/format";
import { shippingIcons, shippingMethods } from "../data/checkout";
import { Button } from "../components/ui/Button";
import { CartLineItem } from "../components/cart/CartLineItem";
import { PriceSummary } from "../components/cart/PriceSummary";
import { CheckoutStepper } from "../components/checkout/CheckoutStepper";
import { AddressForm, EMPTY_ADDRESS, type Address } from "../components/checkout/AddressForm";
import { PaymentOptions } from "../components/checkout/PaymentOptions";
import { OrderConfirmation } from "../components/checkout/OrderConfirmation";
import type { PaymentMethod, PlacedOrder, ShippingMethod } from "../types/checkout";

function generateOrderId(): string {
  let digits = "";
  for (let index = 0; index < 15; index += 1) digits += Math.floor(Math.random() * 10);
  return `OD${digits}`;
}

export default function CheckoutPage() {
  const { items, promoCode, clearCart } = useCart();
  const [step, setStep] = useState(1);
  const [address, setAddress] = useState<Address>(EMPTY_ADDRESS);
  const [shipping, setShipping] = useState<ShippingMethod>(shippingMethods[0]);
  const [payment, setPayment] = useState<PaymentMethod | null>(null);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [order, setOrder] = useState<PlacedOrder | null>(null);

  if (!order && items.length === 0) return <Navigate to="/cart" replace />;
  if (order) return <OrderConfirmation order={order} />;

  const lines = items.flatMap((item) => {
    const product = productById.get(item.productId);
    return product ? [{ product, quantity: item.quantity, variant: item.variant }] : [];
  });
  const totals = computeCartTotals(items, promoCode, shipping.fee);

  const placeOrder = () => {
    if (!payment || !acceptedTerms || processing) return;
    setProcessing(true);
    const slowest = Math.max(...lines.map((line) => line.product.delivery.estimatedDays));
    const placedOrder: PlacedOrder = {
      id: generateOrderId(),
      createdAt: new Date().toISOString(),
      deliveryDate: formatDeliveryDate(Math.max(1, slowest + shipping.additionalDays)),
      address,
      shippingMethod: shipping,
      paymentMethod: payment,
      items: [...items],
      totals,
    };
    window.setTimeout(() => {
      setOrder(placedOrder);
      clearCart();
      setProcessing(false);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }, 650);
  };

  return (
    <div className="flex flex-col gap-3 pb-[calc(82px+env(safe-area-inset-bottom))] lg:pb-0">
      <CheckoutStepper current={step} />
      <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[65fr_35fr]">
        <div className="flex flex-col gap-3">
          {step === 1 && <AddressForm value={address} onChange={setAddress} onSubmit={() => setStep(2)} />}
          {step > 1 && <AddressSummary address={address} onEdit={() => setStep(1)} />}

          {step === 2 && (
            <>
              <fieldset className="bg-white" aria-labelledby="delivery-method-title">
                <legend id="delivery-method-title" className="w-full bg-fk-blue px-4 py-3 text-fk-md font-medium uppercase tracking-wide text-white sm:px-6">Delivery Method</legend>
                <div className="divide-y divide-fk-border">
                  {shippingMethods.map((method) => {
                    const Icon = shippingIcons[method.id];
                    return <label key={method.id} className={`flex min-h-20 cursor-pointer items-start gap-3 px-4 py-4 sm:px-6 ${shipping.id === method.id ? "bg-blue-50" : "hover:bg-fk-bg"}`}><input type="radio" name="shipping" checked={shipping.id === method.id} onChange={() => setShipping(method)} className="mt-1 h-4 w-4 accent-fk-blue" /><Icon className="mt-0.5 h-5 w-5 text-fk-blue" /><span className="min-w-0 flex-1"><strong className="block text-fk-md text-fk-ink">{method.label}</strong><span className="text-fk-sm text-fk-muted">{method.description}</span></span><strong className="text-fk-md text-fk-ink">{method.fee ? formatINR(method.fee) : "Free"}</strong></label>;
                  })}
                </div>
              </fieldset>

              <section className="flex flex-col gap-3" data-testid="order-summary" aria-labelledby="review-items-title">
                <h2 id="review-items-title" className="bg-white px-4 py-3 text-fk-md font-medium uppercase tracking-wide text-fk-blue sm:px-6">Review Items</h2>
                {lines.map(({ product, quantity, variant }) => <CartLineItem key={`${product.id}:${variant ?? "default"}`} product={product} quantity={quantity} variant={variant} readOnly />)}
              </section>
              <div className="flex justify-end bg-white p-4 sm:p-6"><Button variant="cart" className="min-h-12 w-full sm:w-auto" onClick={() => setStep(3)} data-testid="continue-to-payment-button">Continue to Payment</Button></div>
            </>
          )}

          {step === 3 && (
            <>
              <button onClick={() => setStep(2)} className="min-h-11 self-start bg-white px-4 py-3 text-fk-md font-medium text-fk-blue sm:px-6" data-testid="edit-order-summary">Back to Order Summary</button>
              <PaymentOptions value={payment} onChange={setPayment} />
              <div className="bg-white p-4 sm:p-6">
                <label className="flex cursor-pointer items-start gap-3 text-fk-base text-fk-ink"><input type="checkbox" checked={acceptedTerms} onChange={(event) => setAcceptedTerms(event.target.checked)} className="mt-0.5 h-4 w-4 accent-fk-blue" /><span>I agree to the demo store terms and confirm that the order details are correct.</span></label>
                {!payment && <p className="mt-3 text-fk-sm text-fk-flame">Select a payment method to place your order.</p>}
                <Button variant="buy" onClick={placeOrder} disabled={!payment || !acceptedTerms || processing} className="mt-5 min-h-12 w-full" data-testid="confirm-order-button"><LockKeyhole className="h-4 w-4" />{processing ? "Processing Order…" : `Place Order · ${formatINR(totals.totalAmount)}`}</Button>
                <p className="mt-2 text-center text-fk-sm text-fk-muted">100% secure demo checkout · No real payment is processed</p>
              </div>
            </>
          )}
        </div>
        <PriceSummary totals={totals} />
      </div>

      {step === 3 && (
        <div className="fixed inset-x-0 bottom-0 z-40 flex items-center gap-3 border-t border-fk-border bg-white px-4 py-3 shadow-[0_-2px_8px_rgba(0,0,0,0.12)] [padding-bottom:calc(0.75rem+env(safe-area-inset-bottom))] lg:hidden">
          <strong className="text-fk-lg text-fk-ink">{formatINR(totals.totalAmount)}</strong>
          <Button variant="buy" className="min-h-12 flex-1" onClick={placeOrder} disabled={!payment || !acceptedTerms || processing}>{processing ? "Processing…" : "Place Order"}</Button>
        </div>
      )}
    </div>
  );
}

function AddressSummary({ address, onEdit }: { address: Address; onEdit: () => void }) {
  return (
    <section className="flex items-start justify-between gap-4 bg-white p-4 sm:p-6" aria-labelledby="deliver-to-title">
      <div className="min-w-0"><h2 id="deliver-to-title" className="text-fk-md font-medium uppercase tracking-wide text-fk-muted">Deliver to</h2><p className="mt-1 text-fk-md font-medium text-fk-ink">{address.name} <span className="ml-2 font-normal">{address.phone}</span></p><p className="mt-0.5 text-fk-base text-fk-muted">{address.addressLine}, {address.city}, {address.state} — {address.pincode}</p><p className="mt-0.5 text-fk-sm text-fk-muted">{address.email}</p></div>
      <button onClick={onEdit} className="min-h-11 shrink-0 px-2 text-fk-md font-medium text-fk-blue" data-testid="edit-address">Edit</button>
    </section>
  );
}
