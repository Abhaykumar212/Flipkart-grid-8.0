import { Bell, X } from "lucide-react";
import type { InterventionSurfaceProps } from "./surfaceTypes";
import { InterventionWhy } from "./InterventionWhy";

export function NonBlockingBanner({ intervention, reasons, onClick, onDismiss }: InterventionSurfaceProps) {
  return (
    <section className="mx-auto flex w-full max-w-fk items-center gap-3 border-b border-fk-border bg-blue-50 px-4 py-3" role="status" aria-live="polite" data-testid="intervention-banner">
      <Bell className="h-5 w-5 shrink-0 text-fk-blue" aria-hidden="true" />
      <div className="min-w-0 flex-1 text-fk-base text-fk-ink"><p><strong>{intervention.headline ?? intervention.display_name}</strong> {intervention.body ?? intervention.reason}</p><InterventionWhy reasons={reasons} /></div>
      <button type="button" onClick={onClick} className="min-h-11 shrink-0 px-2 text-fk-md font-medium text-fk-blue">{intervention.cta_label ?? "View"}</button>
      <button type="button" onClick={onDismiss} className="flex h-11 w-11 shrink-0 items-center justify-center text-fk-muted" aria-label="Dismiss recommendation"><X className="h-5 w-5" /></button>
    </section>
  );
}
