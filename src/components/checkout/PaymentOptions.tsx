import { Smartphone, CreditCard, Landmark, Banknote, type LucideIcon } from "lucide-react";

export type PaymentMethod = "upi" | "card" | "netbanking" | "cod";

const METHODS: { id: PaymentMethod; label: string; hint: string; icon: LucideIcon }[] = [
  { id: "upi", label: "UPI", hint: "Pay by any UPI app", icon: Smartphone },
  { id: "card", label: "Credit / Debit / ATM Card", hint: "Add and secure cards as per RBI guidelines", icon: CreditCard },
  { id: "netbanking", label: "Net Banking", hint: "This instrument has low success, use UPI or cards", icon: Landmark },
  { id: "cod", label: "Cash on Delivery", hint: "Pay in cash when your order arrives", icon: Banknote },
];

interface PaymentOptionsProps {
  value: PaymentMethod;
  onChange: (method: PaymentMethod) => void;
}

/**
 * Presentational only — no card/UPI inputs behind any option, by design. This is
 * a demo shell, so nothing here collects or transmits payment details.
 */
export function PaymentOptions({ value, onChange }: PaymentOptionsProps) {
  return (
    <fieldset className="bg-white" data-testid="payment-options">
      <legend className="w-full bg-fk-blue px-4 py-3 text-fk-md font-medium uppercase tracking-wide text-white sm:px-6">
        Payment Options
      </legend>

      <div className="divide-y divide-fk-border">
        {METHODS.map(({ id, label, hint, icon: Icon }) => (
          <label
            key={id}
            className={`flex cursor-pointer items-start gap-3 px-4 py-4 sm:px-6 ${
              value === id ? "bg-fk-bg" : "hover:bg-fk-bg/60"
            }`}
          >
            <input
              type="radio"
              name="payment-method"
              value={id}
              checked={value === id}
              onChange={() => onChange(id)}
              className="mt-1 h-4 w-4 shrink-0 accent-fk-blue"
            />
            <Icon className="mt-0.5 h-5 w-5 shrink-0 text-fk-muted" strokeWidth={2} />
            <span className="min-w-0">
              <span className="block text-fk-md text-fk-ink">{label}</span>
              <span className="block text-fk-sm text-fk-muted">{hint}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
