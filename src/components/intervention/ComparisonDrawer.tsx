import { GitCompareArrows, X } from "lucide-react";
import { useSession } from "../../context/SessionContext";
import { useTracker } from "../../context/TrackerContext";
import { products } from "../../data/products";
import type { InterventionSurfaceProps } from "./surfaceTypes";

export function ComparisonDrawer({ intervention, onClick, onDismiss }: InterventionSurfaceProps) {
  const { emit } = useSession();
  const { snapshot } = useTracker();
  const sourceId = snapshot?.session.current_product_id ?? snapshot?.cart.items[0]?.product_id;
  const alternatives = products.filter((product) => product.id !== sourceId).slice(0, 3);

  const compare = () => {
    onClick();
    if (!sourceId || alternatives.length === 0) return;
    emit("PRODUCT_COMPARED", {
      productId: sourceId,
      metadata: { compared_with: alternatives.map((product) => product.id) },
    });
  };

  return (
    <aside className="fixed inset-x-2 bottom-2 z-30 mx-auto max-w-2xl border border-fk-border bg-white p-4 shadow-fk-hover sm:inset-x-auto sm:right-3 sm:w-[440px]" role="status" aria-live="polite" data-testid="intervention-comparison-drawer">
      <div className="flex items-start gap-3"><GitCompareArrows className="mt-0.5 h-5 w-5 text-fk-blue" /><div className="min-w-0 flex-1"><p className="font-medium text-fk-ink">{intervention.headline ?? "Compare before you decide"}</p><p className="mt-1 text-fk-base text-fk-muted">{intervention.body ?? intervention.reason}</p></div><button type="button" onClick={onDismiss} className="flex h-11 w-11 items-center justify-center text-fk-muted" aria-label="Dismiss comparison"><X className="h-5 w-5" /></button></div>
      <button type="button" onClick={compare} className="mt-3 min-h-11 font-medium text-fk-blue">{intervention.cta_label ?? "Compare options"}</button>
    </aside>
  );
}
