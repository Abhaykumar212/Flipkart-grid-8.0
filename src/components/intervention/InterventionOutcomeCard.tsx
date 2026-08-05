import { motion } from "framer-motion";
import { CheckCircle2, X, ShoppingBag, Truck, Zap, BellRing, CreditCard, UserCheck, Mail } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { InterventionOutcome, OutcomeKind } from "../../lib/interventionOutcomes";
import { useReducedMotion } from "./useReducedMotion";

const ICON: Record<OutcomeKind, LucideIcon> = {
  discount: ShoppingBag,
  free_delivery: Truck,
  express_delivery: Zap,
  emi: CreditCard,
  price_alert: BellRing,
  payment_saved: CreditCard,
  account_created: UserCheck,
  email_scheduled: Mail,
};

/**
 * The result of accepting an intervention — rendered where `AmbientCard`
 * just was, so accepting reads as "here's what happened" rather than the
 * card just vanishing. Same bottom-right dock, deliberately different
 * (green, checkmarked) chrome so it can never be mistaken for a new
 * suggestion. Stays open until dismissed — no auto-timeout, same as every
 * other surface.
 */
export function InterventionOutcomeCard({ outcome, onDismiss }: { outcome: InterventionOutcome; onDismiss: () => void }) {
  const reducedMotion = useReducedMotion();
  const Icon = ICON[outcome.kind];

  return (
    <motion.div
      className="fixed bottom-24 right-5 z-[9980] w-[min(320px,calc(100vw-40px))]"
      initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 24, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.96 }}
      transition={{ duration: reducedMotion ? 0.15 : 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="relative overflow-hidden rounded-2xl border-2 border-fk-green/50 bg-white/95 p-4 shadow-fk-glow backdrop-blur-xl">
        <span
          aria-hidden
          className="pointer-events-none absolute -right-6 -top-6 h-20 w-20 rounded-full bg-fk-green/10"
        />
        <div className="relative mb-2 flex items-center justify-between">
          <span className="inline-flex items-center gap-1 rounded-full bg-fk-green px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white shadow-sm">
            <CheckCircle2 className="h-3 w-3" />
            Done
          </span>
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss"
            className="rounded-full p-1 text-fk-muted transition hover:bg-black/5 hover:text-fk-ink"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
        <div className="relative flex items-start gap-2.5">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-fk-green/15 text-fk-green">
            <Icon className="h-4 w-4" strokeWidth={2.25} />
          </span>
          <div className="min-w-0">
            <h3 className="text-fk-md font-bold text-fk-ink">{outcome.title}</h3>
            <p className="mt-0.5 text-fk-sm leading-5 text-fk-ink/80">{outcome.body}</p>
            {outcome.detail && <p className="mt-1.5 text-fk-xs text-fk-muted">{outcome.detail}</p>}
            {outcome.promo && (
              <span className="mt-2 inline-flex items-center rounded-md border border-dashed border-fk-green/60 bg-fk-green/5 px-2 py-1 font-mono text-fk-sm font-bold tracking-wide text-fk-green">
                {outcome.promo.code}
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
