import { useEffect, useState } from "react";
import { Sparkles, X } from "lucide-react";
import { apiGet } from "../../lib/api";
import type { InterventionSurfaceProps } from "./surfaceTypes";

export function InlineCartCard({ intervention, onClick, onDismiss }: InterventionSurfaceProps) {
  const [summary, setSummary] = useState<{ pros: string[]; cons: string[] } | null>(null);
  useEffect(() => {
    if (intervention.type !== "REVIEW_SUMMARY" || !intervention.review_product_id) return;
    void apiGet<{ pros: string[]; cons: string[] }>(`/api/v1/products/${encodeURIComponent(intervention.review_product_id)}/review-summary`)
      .then(setSummary)
      .catch(() => setSummary(null));
  }, [intervention.review_product_id, intervention.type]);
  return (
    <section className="border-l-4 border-fk-blue bg-white px-4 py-4 shadow-fk-card sm:px-6" role="status" aria-live="polite" data-testid="intervention-inline-card">
      <div className="flex items-start gap-3">
        <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-fk-blue" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="text-fk-md font-medium text-fk-ink">{intervention.headline ?? intervention.display_name}</p>
          <p className="mt-1 text-fk-base text-fk-muted">{intervention.body ?? intervention.reason}</p>
          {summary && <div className="mt-3 grid gap-3 text-fk-sm sm:grid-cols-2" data-testid="grounded-review-summary">
            <div><p className="font-medium text-emerald-700">Pros</p><ul className="mt-1 list-disc space-y-1 pl-4 text-fk-muted">{summary.pros.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul></div>
            <div><p className="font-medium text-rose-700">Cons</p><ul className="mt-1 list-disc space-y-1 pl-4 text-fk-muted">{summary.cons.slice(0, 2).map((item) => <li key={item}>{item}</li>)}</ul></div>
          </div>}
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
