import { Sparkles, Zap } from "lucide-react";
import { Button } from "../ui/Button";
import { formatINR } from "../../lib/format";
import type { CartTotals } from "../../lib/cartTotals";

interface PriceSummaryProps {
  totals: CartTotals;
  /** Omit to render the summary with no CTA (checkout drives its own buttons). */
  action?: { label: string; onClick?: () => void; testId?: string };
}

export function PriceSummary({ totals, action }: PriceSummaryProps) {
  const {
    itemCount,
    totalMrp,
    discount,
    deliveryCharge,
    isDeliveryFree,
    totalAmount,
    savings,
    promoApplied,
    expressDelivery,
  } = totals;

  return (
    <div className="sticky top-20">
      <div className="bg-white">
        <h2 className="border-b border-fk-border px-6 py-4 text-fk-md font-medium uppercase tracking-wide text-fk-muted">
          Price Details
        </h2>

        <div className="flex flex-col gap-4 px-6 py-4 text-fk-md text-fk-ink">
          <div className="flex items-center justify-between">
            <span>
              Price ({itemCount} {itemCount === 1 ? "item" : "items"})
            </span>
            <span>{formatINR(totalMrp)}</span>
          </div>

          <div className="flex items-center justify-between">
            <span>Discount</span>
            <span className="text-fk-green">− {formatINR(discount)}</span>
          </div>

          <div className="flex items-center justify-between">
            <span>Delivery Charges</span>
            {isDeliveryFree ? (
              <span className="text-fk-green">Free</span>
            ) : (
              <span>{formatINR(deliveryCharge)}</span>
            )}
          </div>

          {promoApplied && (
            <div className="flex items-center justify-between rounded-md bg-fk-green/10 px-2.5 py-2 text-fk-sm">
              <span className="flex items-center gap-1.5 font-medium text-fk-green">
                <Sparkles className="h-3.5 w-3.5" />
                {promoApplied.label}
              </span>
              <span className="font-semibold text-fk-green">− {formatINR(promoApplied.amountOff)}</span>
            </div>
          )}

          {expressDelivery && (
            <div className="flex items-center gap-1.5 text-fk-sm font-medium text-fk-blue">
              <Zap className="h-3.5 w-3.5" />
              Express delivery unlocked
            </div>
          )}

          <div className="flex items-center justify-between border-y border-dashed border-fk-border py-4 text-fk-lg font-bold">
            <span>Total Amount</span>
            <span data-testid="cart-total-amount">{formatINR(totalAmount)}</span>
          </div>

          {savings > 0 && (
            <p className="text-fk-md font-medium text-fk-green">
              You will save {formatINR(savings)} on this order
            </p>
          )}
        </div>
      </div>

      {action && (
        <Button
          variant="buy"
          className="mt-3 w-full"
          onClick={action.onClick}
          data-testid={action.testId}
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}
