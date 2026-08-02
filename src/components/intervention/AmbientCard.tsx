import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { IntelligenceGlow } from "./IntelligenceGlow";
import { useEscapeDismiss } from "./useEscapeDismiss";
import { useReducedMotion } from "./useReducedMotion";
import type { InterventionContentProps } from "./types";

const AUTO_DISMISS_MS = 12000;

/**
 * Rung 1. Small frosted card docked bottom-right, above AgentInspector's
 * debug pill (fixed bottom-5 right-5). Slides and fades in, dismissible,
 * auto-fades after ~12s. Manages its own open/close animation and only
 * calls onDismiss once the exit transition has actually finished.
 */
export function AmbientCard({ title, body, actionLabel, onAction, onDismiss, reasonText }: InterventionContentProps) {
  const [open, setOpen] = useState(true);
  const reducedMotion = useReducedMotion();
  const close = useCallback(() => setOpen(false), []);

  useEscapeDismiss(open, close);

  useEffect(() => {
    const timer = setTimeout(close, AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [close]);

  return (
    <AnimatePresence onExitComplete={onDismiss}>
      {open && (
        <motion.div
          className="fixed bottom-24 right-5 z-[9980] w-[min(320px,calc(100vw-40px))]"
          initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.96 }}
          transition={{ duration: reducedMotion ? 0.15 : 0.4, ease: "easeOut" }}
        >
          <IntelligenceGlow intensity="subtle" rounded="rounded-2xl">
            <div className="relative rounded-2xl border border-white/60 bg-white/70 p-4 shadow-fk-glow backdrop-blur-xl">
              <button
                type="button"
                onClick={close}
                aria-label="Dismiss"
                className="absolute right-2.5 top-2.5 rounded-full p-1 text-fk-muted transition hover:bg-black/5 hover:text-fk-ink"
              >
                <X className="h-3.5 w-3.5" />
              </button>
              <h3 className="pr-5 text-fk-md font-semibold text-fk-ink">{title}</h3>
              <p className="mt-1 text-fk-sm leading-5 text-fk-ink/80">{body}</p>
              <p className="mt-2 text-fk-xs text-fk-muted">{reasonText}</p>
              {actionLabel && onAction && (
                <button
                  type="button"
                  onClick={onAction}
                  className="mt-3 inline-flex items-center rounded-full bg-fk-blue px-4 py-1.5 text-fk-sm font-medium text-white transition hover:bg-fk-blue-dark"
                >
                  {actionLabel}
                </button>
              )}
            </div>
          </IntelligenceGlow>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
