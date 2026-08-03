import type { DecisionOutcome } from "../../types/dashboard";

export function OutcomeBadge({ outcome }: { outcome: DecisionOutcome | null }) {
  const label = outcome?.order_completed
    ? "Converted"
    : outcome?.dismissed
      ? "Dismissed"
      : outcome?.clicked
        ? "Clicked"
        : outcome?.intervention_shown
          ? "Shown"
          : "Open";
  const tone = outcome?.order_completed
    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
    : outcome?.dismissed
      ? "border-rose-500/30 bg-rose-500/10 text-rose-200"
      : outcome?.clicked
        ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-200"
        : "border-slate-700 bg-slate-900 text-slate-300";
  return <span className={`inline-flex rounded-md border px-2 py-1 text-[11px] font-semibold ${tone}`}>{label}</span>;
}
