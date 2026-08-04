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
          <IntelligenceGlow intensity="present" rounded="rounded-2xl">
            <div className="relative rounded-2xl border-2 border-fk-blue/40 bg-white/95 p-4 shadow-fk-glow backdrop-blur-xl">
              <div className="mb-2 flex items-center justify-between">
                <span className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white shadow-sm">
                  ✨ AI Intervention
                </span>
                <button
                  type="button"
                  onClick={close}
                  aria-label="Dismiss"
                  className="rounded-full p-1 text-fk-muted transition hover:bg-black/5 hover:text-fk-ink"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
              <h3 className="pr-2 text-fk-md font-bold text-fk-ink">{title}</h3>
              <p className="mt-1 text-fk-sm leading-5 text-fk-ink/80">{body}</p>
              <p className="mt-2 text-fk-xs text-fk-blue font-medium">{reasonText}</p>
              {actionLabel && onAction && (
                <button
                  type="button"
                  onClick={() => {
                    onAction();
                    close();
                  }}
                  className="mt-3 w-full inline-flex items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-fk-blue to-blue-700 px-4 py-2 text-fk-sm font-semibold text-white shadow-md transition hover:scale-[1.02] active:scale-[0.98]"
                >
                  {actionLabel} →
                </button>
              )}
            </div>
          </IntelligenceGlow>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
