import { useState } from "react";
import { ChevronDown, CreditCard } from "lucide-react";
import type { Emi } from "../../types/product";
import { formatINR } from "../../lib/format";

export function EMICalculator({ sellingPrice, emi }: { sellingPrice: number; emi?: Emi }) {
  const [expanded, setExpanded] = useState(false);
  if (!emi) return null;

  const monthOptions = [...new Set([3, 6, 12, emi.months])].sort((a, b) => a - b);
  return (
    <section className="mt-4 border border-fk-border bg-fk-bg p-4" aria-labelledby="emi-heading">
      <div className="flex items-center gap-2">
        <CreditCard className="h-5 w-5 text-fk-blue" aria-hidden="true" />
        <h2 id="emi-heading" className="text-fk-md font-medium text-fk-ink">EMI options</h2>
      </div>
      <p className="mt-2 text-fk-base text-fk-ink">
        Listed plan: <strong>{formatINR(emi.monthly)} × {emi.months} months</strong>
      </p>

      {expanded && (
        <div className="mt-3 overflow-hidden border border-fk-border bg-white">
          {monthOptions.map((months) => {
            const listed = months === emi.months;
            const monthly = listed ? emi.monthly : Math.ceil(sellingPrice / months);
            return (
              <div key={months} className="flex items-center justify-between gap-3 border-b border-fk-border px-3 py-2.5 last:border-0">
                <span className="text-fk-sm text-fk-muted">{months} months</span>
                <span className="text-right text-fk-base font-medium text-fk-ink">
                  {formatINR(monthly)}/month
                  <span className="ml-2 text-fk-xs font-normal text-fk-muted">
                    {listed ? "listed" : "principal-only estimate"}
                  </span>
                </span>
              </div>
            );
          })}
        </div>
      )}

      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((current) => !current)}
        className="mt-3 inline-flex min-h-11 items-center gap-1 text-fk-sm font-medium text-fk-blue"
      >
        {expanded ? "Hide estimates" : "Compare monthly estimates"}
        <ChevronDown className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`} aria-hidden="true" />
      </button>
      <p className="text-fk-xs text-fk-muted">Interest, bank eligibility, and final charges are confirmed at checkout.</p>
    </section>
  );
}
