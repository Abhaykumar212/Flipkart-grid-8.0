import { Sparkles, X } from "lucide-react";
import type { InterventionSurfaceProps } from "./surfaceTypes";

export function InlineCartCard({ intervention, onClick, onDismiss }: InterventionSurfaceProps) {
  return (
    <section className="border-l-4 border-fk-blue bg-white px-4 py-4 shadow-fk-card sm:px-6" role="status" aria-live="polite" data-testid="intervention-inline-card">
      <div className="flex items-start gap-3">
        <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-fk-blue" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="text-fk-md font-medium text-fk-ink">{intervention.headline ?? intervention.display_name}</p>
          <p className="mt-1 text-fk-base text-fk-muted">{intervention.body ?? intervention.reason}</p>
          <button type="button" onClick={onClick} className="mt-3 min-h-11 text-fk-md font-medium text-fk-blue">
            {intervention.cta_label ?? "See details"}
          </button>
        </div>
        <button type="button" onClick={onDismiss} className="flex h-11 w-11 shrink-0 items-center justify-center text-fk-muted" aria-label="Dismiss recommendation">
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}
