import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { computeCartTotals } from "../lib/cartTotals";
import { productById } from "../data/products";
import { formatDeliveryDate } from "../lib/format";
import { userHistory } from "../lib/userHistory";
import { eventTimeline } from "../lib/eventTimeline";
import { Button } from "../components/ui/Button";
import { CartLineItem } from "../components/cart/CartLineItem";
import { PriceSummary } from "../components/cart/PriceSummary";
import { CheckoutStepper } from "../components/checkout/CheckoutStepper";
import {
  AddressForm,
  EMPTY_ADDRESS,
  type Address,
} from "../components/checkout/AddressForm";
import { PaymentOptions, type PaymentMethod } from "../components/checkout/PaymentOptions";
import { OrderConfirmation } from "../components/checkout/OrderConfirmation";

interface PlacedOrder {
  id: string;
  deliveryDate: string;
}

/** localStorage-persisted mock account, set by the Navbar sign-in modal. See src/context/AuthContext.tsx. */
function currentUserId(): string | undefined {
  try {
    const raw = localStorage.getItem("fk-user-v1");
    return raw ? (JSON.parse(raw).id as string) : undefined;
  } catch {
    return undefined;
  }
}

export default function CheckoutPage() {
  const { items, clearCart, appliedPromo, freeDeliveryUnlocked, expressDeliveryUnlocked } = useCart();

  const [step, setStep] = useState(1);
  const [address, setAddress] = useState<Address>(EMPTY_ADDRESS);
  const [payment, setPayment] = useState<PaymentMethod>("upi");
  const [order, setOrder] = useState<PlacedOrder | null>(null);
  const [placing, setPlacing] = useState(false);
  const [placeError, setPlaceError] = useState<string | null>(null);

  // Nothing to check out. Guard is skipped once an order exists, otherwise
  // clearing the cart on confirm would bounce the user off their own receipt.
  if (!order && items.length === 0) return <Navigate to="/cart" replace />;

  if (order) {
    return <OrderConfirmation orderId={order.id} deliveryDate={order.deliveryDate} />;
  }

  const lines = items.flatMap((item) => {
    const product = productById.get(item.productId);
    return product ? [{ product, quantity: item.quantity }] : [];
  });
  const totals = computeCartTotals(items, {
    promoAmountOff: appliedPromo?.amountOff,
    promoLabel: appliedPromo?.label,
    freeDelivery: freeDeliveryUnlocked,
    expressDelivery: expressDeliveryUnlocked,
  });

  const placeOrder = async () => {
    // Slowest item in the cart determines when the whole order lands. Computed
    // here because `lines` is empty the moment the cart is cleared below.
    const slowest = Math.max(...lines.map((l) => l.product.delivery.estimatedDays));
    setPlacing(true);
    setPlaceError(null);

    // Real backend order (backend/orders.py) — explicit test-mode "payment",
    // no processor involved (see the "Test Mode" banner below). Falls back to
    // a client-only order id if the backend is unreachable so the demo never
    // hard-blocks on the network, but that path is the exception, not the design.
    let orderId: string | null = null;
    try {
      const response = await fetch("http://localhost:8000/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: eventTimeline.getSessionId(),
          user_id: currentUserId() ?? null,
          items: lines.map(({ product, quantity }) => ({
            product_id: product.id,
            title: product.title,
            quantity,
            selling_price: product.price.sellingPrice,
          })),
          address: {
            name: address.name,
            phone: address.phone,
            address_line: address.addressLine,
            city: address.city,
            state: address.state,
            pincode: address.pincode,
          },
          payment_method: payment,
          total_inr: totals.totalSellingPrice,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        orderId = data.order_id;
      } else {
        setPlaceError("Payment gateway (test mode) didn't confirm the order — showing a local receipt instead.");
      }
    } catch {
      setPlaceError("Couldn't reach the order service — showing a local receipt instead.");
    }

    const finalOrderId =
      orderId ?? `OD${Array.from({ length: 15 }, () => Math.floor(Math.random() * 10)).join("")}`;

    setOrder({ id: finalOrderId, deliveryDate: formatDeliveryDate(slowest) });
    userHistory.recordPurchase(lines.map((line) => line.product.id));

    // The end-to-end conversion event: closes the TODO that used to sit here.
    eventTimeline.recordOrderCompleted(finalOrderId, totals.totalSellingPrice, lines.length);
    void eventTimeline.flush(true);

    clearCart();
    setPlacing(false);
  };

  return (
    <div className="flex flex-col gap-3">
      <CheckoutStepper current={step} />

      <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[65fr_35fr]">
        <div className="flex flex-col gap-3">
          {step === 1 && (
            <AddressForm
              value={address}
              onChange={setAddress}
              onSubmit={() => setStep(2)}
            />
          )}

          {step > 1 && <AddressSummary address={address} onEdit={() => setStep(1)} />}

          {step === 2 && (
            <>
              <div className="flex flex-col gap-3" data-testid="order-summary">
                {lines.map(({ product, quantity }) => (
                  <CartLineItem
                    key={product.id}
                    product={product}
                    quantity={quantity}
                    readOnly
                  />
                ))}
              </div>
              <div className="bg-white p-4 sm:p-6">
                <Button
                  variant="cart"
                  onClick={() => setStep(3)}
                  data-testid="continue-to-payment-button"
                >
                  Continue
                </Button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <button
                onClick={() => setStep(2)}
                className="self-start bg-white px-4 py-3 text-fk-md text-fk-blue sm:px-6"
                data-testid="edit-order-summary"
              >
                ← Back to Order Summary
              </button>
              <PaymentOptions value={payment} onChange={setPayment} />
              <div className="bg-white p-4 sm:p-6">
                <div className="mb-3 flex items-center gap-2 rounded bg-amber-50 px-3 py-2 text-fk-sm text-amber-800">
                  <span className="font-semibold">Test Mode</span>
                  <span>— no real payment is processed; this creates a real order record for the demo.</span>
                </div>
                {placeError && (
                  <p className="mb-3 text-fk-sm text-fk-flame">{placeError}</p>
                )}
                <Button
                  variant="buy"
                  onClick={placeOrder}
                  disabled={placing}
                  data-testid="confirm-order-button"
                >
                  {placing ? "Placing Order…" : "Place Order"}
                </Button>
              </div>
            </>
          )}
        </div>

        <PriceSummary totals={totals} />
      </div>
    </div>
  );
}

function AddressSummary({ address, onEdit }: { address: Address; onEdit: () => void }) {
  return (
    <div className="flex items-start justify-between gap-4 bg-white p-4 sm:p-6">
      <div className="min-w-0">
        <h2 className="text-fk-md font-medium uppercase tracking-wide text-fk-muted">
          Deliver to
        </h2>
        <p className="mt-1 text-fk-md font-medium text-fk-ink">
          {address.name} <span className="ml-2 font-normal">{address.phone}</span>
        </p>
        <p className="mt-0.5 text-fk-base text-fk-muted">
          {address.addressLine}, {address.city}, {address.state} — {address.pincode}
        </p>
      </div>
      <button
        onClick={onEdit}
        className="shrink-0 text-fk-md font-medium text-fk-blue"
        data-testid="edit-address"
      >
        Edit
      </button>
    </div>
  );
}
