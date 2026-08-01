import { ShieldCheck } from "lucide-react";
import { paymentMethods } from "../../data/checkout";
import type { PaymentMethod } from "../../types/checkout";

export type { PaymentMethod } from "../../types/checkout";

interface PaymentOptionsProps {
  value: PaymentMethod | null;
  onChange: (method: PaymentMethod) => void;
}

export function PaymentOptions({ value, onChange }: PaymentOptionsProps) {
  return (
    <fieldset className="bg-white" data-testid="payment-options">
      <legend className="w-full bg-fk-blue px-4 py-3 text-fk-md font-medium uppercase tracking-wide text-white sm:px-6">Payment Options</legend>
      <div className="divide-y divide-fk-border">
        {paymentMethods.map(({ id, label, hint, icon: Icon }) => (
          <label key={id} className={`flex min-h-16 cursor-pointer items-start gap-3 px-4 py-4 sm:px-6 ${value === id ? "bg-blue-50" : "hover:bg-fk-bg/60"}`}>
            <input type="radio" name="payment-method" value={id} checked={value === id} onChange={() => onChange(id)} className="mt-1 h-4 w-4 shrink-0 accent-fk-blue" />
            <Icon className="mt-0.5 h-5 w-5 shrink-0 text-fk-muted" strokeWidth={2} />
            <span className="min-w-0"><span className="block text-fk-md font-medium text-fk-ink">{label}</span><span className="block text-fk-sm text-fk-muted">{hint}</span></span>
          </label>
        ))}
      </div>
      <div className="flex items-start gap-2 border-t border-fk-border bg-fk-bg px-4 py-3 text-fk-sm text-fk-muted sm:px-6"><ShieldCheck className="h-4 w-4 shrink-0 text-fk-green" />Demo checkout only. No payment details are collected and no real charge is made.</div>
    </fieldset>
  );
}
