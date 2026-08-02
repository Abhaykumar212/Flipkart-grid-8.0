import { ShieldCheck, X } from "lucide-react";
import type { InterventionSurfaceProps } from "./surfaceTypes";

export function CheckoutAssistPanel({ intervention, onClick, onDismiss }: InterventionSurfaceProps) {
  return (
    <section className="border border-fk-border bg-blue-50 px-4 py-4 sm:px-6" role="status" aria-live="polite" data-testid="intervention-checkout-panel">
      <div className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-fk-blue" />
        <div className="min-w-0 flex-1"><p className="text-fk-md font-medium text-fk-ink">{intervention.headline ?? intervention.display_name}</p><p className="mt-1 text-fk-base text-fk-muted">{intervention.body ?? intervention.reason}</p><button type="button" onClick={onClick} className="mt-2 min-h-11 font-medium text-fk-blue">{intervention.cta_label ?? "Try another option"}</button></div>
        <button type="button" onClick={onDismiss} className="flex h-11 w-11 items-center justify-center text-fk-muted" aria-label="Dismiss checkout help"><X className="h-5 w-5" /></button>
      </div>
    </section>
  );
}
