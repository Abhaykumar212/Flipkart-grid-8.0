import { Check } from "lucide-react";

export const CHECKOUT_STEPS = ["Delivery Address", "Order Summary", "Payment"] as const;

interface CheckoutStepperProps {
  /** 1-based index of the active step. */
  current: number;
}

export function CheckoutStepper({ current }: CheckoutStepperProps) {
  return (
    <ol className="flex items-center bg-white px-4 py-5 sm:px-8" data-testid="checkout-stepper">
      {CHECKOUT_STEPS.map((label, i) => {
        const step = i + 1;
        const isComplete = step < current;
        const isActive = step === current;

        return (
          <li key={label} className="flex flex-1 items-center last:flex-none">
            <div className="flex items-center gap-2">
              <span
                aria-current={isActive ? "step" : undefined}
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-fk-sm font-medium ${
                  isComplete
                    ? "bg-fk-green text-white"
                    : isActive
                      ? "bg-fk-blue text-white"
                      : "border border-fk-border bg-white text-fk-muted"
                }`}
              >
                {isComplete ? <Check className="h-4 w-4" strokeWidth={3} /> : step}
              </span>
              <span
                className={`hidden text-fk-md sm:inline ${
                  isActive
                    ? "font-medium text-fk-blue"
                    : isComplete
                      ? "text-fk-ink"
                      : "text-fk-muted"
                }`}
              >
                {label}
              </span>
            </div>

            {step < CHECKOUT_STEPS.length && (
              <span
                className={`mx-3 h-px flex-1 ${isComplete ? "bg-fk-green" : "bg-fk-border"}`}
                aria-hidden="true"
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
