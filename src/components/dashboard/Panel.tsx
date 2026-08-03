import type { ReactNode } from "react";

/**
 * Shared shells for the operations console.
 *
 * Every dashboard panel used to hand-roll its own border and background, which
 * is how one card ended up rendering white on a dark page. Centralising the
 * chrome keeps the surface consistent as pages get added.
 */

export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl border border-slate-800 bg-slate-900 ${className}`}>
      {(title || action) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold text-white">{title}</h2>}
            {subtitle && <p className="mt-1 text-xs leading-relaxed text-slate-400">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function StatTile({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  const toneClass = {
    default: "text-white",
    good: "text-emerald-300",
    warn: "text-amber-300",
    bad: "text-rose-300",
  }[tone];
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/50 px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className={`mt-1.5 text-xl font-semibold tabular-nums ${toneClass}`}>{value}</p>
      {hint && <p className="mt-1 text-[11px] leading-snug text-slate-500">{hint}</p>}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">{eyebrow}</p>
        )}
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">{title}</h1>
        {description && <p className="mt-2 max-w-3xl text-sm text-slate-400">{description}</p>}
      </div>
      {action}
    </header>
  );
}

export function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon?: ReactNode;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/50 px-6 py-14 text-center">
      {icon && <div className="mx-auto mb-3 text-slate-500">{icon}</div>}
      <p className="font-medium text-slate-200">{title}</p>
      {children && <div className="mx-auto mt-2 max-w-lg text-sm text-slate-500">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Bar({
  value,
  max,
  tone = "cyan",
}: {
  value: number;
  max: number;
  tone?: "cyan" | "emerald" | "amber" | "rose";
}) {
  const width = max > 0 ? Math.max(1.5, (value / max) * 100) : 0;
  const toneClass = {
    cyan: "bg-cyan-400",
    emerald: "bg-emerald-400",
    amber: "bg-amber-400",
    rose: "bg-rose-400",
  }[tone];
  return (
    <span className="block h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
      <span className={`block h-full rounded-full ${toneClass}`} style={{ width: `${width}%` }} />
    </span>
  );
}
