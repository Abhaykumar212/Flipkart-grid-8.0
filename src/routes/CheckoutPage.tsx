import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { computeCartTotals } from "../lib/cartTotals";
import { productById } from "../data/products";
import { formatDeliveryDate } from "../lib/format";
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

/** Mock order reference in Flipkart's OD-prefixed format. Not a real order. */
function generateOrderId(): string {
  let digits = "";
  for (let i = 0; i < 15; i++) digits += Math.floor(Math.random() * 10);
  return `OD${digits}`;
}

interface PlacedOrder {
  id: string;
  deliveryDate: string;
}

export default function CheckoutPage() {
  const { items, clearCart } = useCart();

  const [step, setStep] = useState(1);
  const [address, setAddress] = useState<Address>(EMPTY_ADDRESS);
  const [payment, setPayment] = useState<PaymentMethod>("upi");
  const [order, setOrder] = useState<PlacedOrder | null>(null);

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
  const totals = computeCartTotals(items);

  const placeOrder = () => {
    // Slowest item in the cart determines when the whole order lands. Computed
    // here because `lines` is empty the moment the cart is cleared below.
    const slowest = Math.max(...lines.map((l) => l.product.delivery.estimatedDays));

    setOrder({ id: generateOrderId(), deliveryDate: formatDeliveryDate(slowest) });

    // TODO(agent): fire an "order_completed" SessionEvent here so the
    // cart-abandonment model can distinguish converted carts from abandoned ones.
    clearCart();
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
                <Button
                  variant="buy"
                  onClick={placeOrder}
                  data-testid="confirm-order-button"
                >
                  Place Order
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
