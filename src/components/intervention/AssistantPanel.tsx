import { MessageCircleQuestion, X } from "lucide-react";
import type { InterventionSurfaceProps } from "./surfaceTypes";

export function AssistantPanel({ intervention, onClick, onDismiss }: InterventionSurfaceProps) {
  return (
    <aside className="fk-intervention fixed bottom-20 right-3 z-30 w-[min(360px,calc(100vw-24px))] rounded-[2px] border border-fk-border bg-white p-4 pl-5 shadow-fk-hover" role="status" aria-live="polite" data-testid="intervention-assistant-panel">
      <div className="flex items-start gap-3">
        <MessageCircleQuestion className="h-5 w-5 shrink-0 text-fk-blue" />
        <div className="min-w-0 flex-1"><p className="font-medium text-fk-ink">{intervention.headline ?? "Need help deciding?"}</p><p className="mt-1 text-fk-base text-fk-muted">{intervention.body ?? intervention.reason}</p></div>
        <button type="button" onClick={onDismiss} className="flex h-11 w-11 items-center justify-center text-fk-muted" aria-label="Dismiss recommendation"><X className="h-5 w-5" /></button>
      </div>
      <button type="button" onClick={onClick} className="mt-3 min-h-11 text-fk-md font-medium text-fk-blue">{intervention.cta_label ?? "Show me"}</button>
    </aside>
  );
}
