import { useNavigate } from "react-router-dom";
import { CircleCheck } from "lucide-react";
import { Button } from "../ui/Button";

interface OrderConfirmationProps {
  orderId: string;
  /** Pre-formatted — computed before the cart was cleared. */
  deliveryDate: string;
}

export function OrderConfirmation({ orderId, deliveryDate }: OrderConfirmationProps) {
  const navigate = useNavigate();

  return (
    <div
      className="flex flex-col items-center gap-3 bg-white px-6 py-16 text-center"
      data-testid="order-confirmation"
    >
      <CircleCheck className="h-16 w-16 text-fk-green" strokeWidth={1.5} />

      <h1 className="text-fk-xl font-medium text-fk-ink">Order Placed!</h1>
      <p className="text-fk-base text-fk-muted">
        Thank you for shopping with us. Your order is confirmed.
      </p>

      <dl className="mt-4 flex flex-col items-center gap-2 text-fk-md">
        <div className="flex items-center gap-2">
          <dt className="text-fk-muted">Order ID</dt>
          <dd className="font-medium text-fk-ink" data-testid="order-id">
            {orderId}
          </dd>
        </div>
        <div className="flex items-center gap-2">
          <dt className="text-fk-muted">Estimated delivery</dt>
          <dd className="font-medium text-fk-green">{deliveryDate}</dd>
        </div>
      </dl>

      <Button variant="primary" className="mt-5" onClick={() => navigate("/")}>
        Continue Shopping
      </Button>
    </div>
  );
}
