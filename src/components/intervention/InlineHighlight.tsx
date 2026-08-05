import type { KeyboardEvent, ReactNode } from "react";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { IntelligenceGlow } from "./IntelligenceGlow";
import { useReducedMotion } from "./useReducedMotion";
import type { InterventionContentProps } from "./types";

interface InlineHighlightProps extends Partial<InterventionContentProps> {
  children: ReactNode;
  /** Drives the glow pulse + caption visibility. Space for the caption is always reserved, so toggling never reflows the page. */
  active?: boolean;
  /**
   * `'glow'` — full animated gradient border, shimmer, caption, dismiss
   * affordance (the original rung-0 treatment).
   *
   * `'quiet'` — a genuinely lower rung: subtle blue background tint, slightly
   * bolder text weight, no animation, no border, no caption, no dismiss.
   */
  variant?: "glow" | "quiet";
}

/**
 * Rung 0. Wraps an existing page element (a spec row, a price, a delivery
 * line) with a gentle glow + a small caption below. There's no room at this
 * scale for a heading or a real button: `title`/`body` become the
 * accessible label, the visible caption is always `reasonText`, and
 * `actionLabel` (if given) renders as an inline text-link next to it.
 *
 * The `'quiet'` variant strips everything down to just a faint tint + bolder
 * text — useful for passive content reordering signals where full glow would
 * be too loud.
 */
/** Shared "ease-out-expo"-ish curve — snappy start, soft landing, reads as smooth rather than springy. */
const EASE = [0.16, 1, 0.3, 1] as const;

export function InlineHighlight({
  title,
  body,
  actionLabel,
  onAction,
  onDismiss,
  reasonText,
  active = true,
  children,
  variant = "glow",
}: InlineHighlightProps) {
  const reducedMotion = useReducedMotion();

  /* ── quiet variant ─────────────────────────────────────────────────── */
  if (variant === "quiet") {
    return (
      <motion.span
        className="inline-flex items-start rounded-md font-semibold"
        style={{ background: "rgba(40,116,240,0.07)" }}
        role="note"
        aria-label={title ? `${title}: ${body ?? ""}` : undefined}
        initial={reducedMotion ? false : { opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: reducedMotion ? 0 : 0.25, ease: EASE }}
      >
        {children}
      </motion.span>
    );
  }

  /* ── glow variant (original) ───────────────────────────────────────── */
  function handleKeyDown(event: KeyboardEvent<HTMLSpanElement>) {
    if (event.key === "Escape") onDismiss?.();
  }

  return (
    <motion.span
      className="inline-flex flex-col items-start align-middle outline-none"
      tabIndex={0}
      role="note"
      aria-label={`${title}: ${body}. ${reasonText}`}
      onKeyDown={handleKeyDown}
      initial={reducedMotion ? false : { opacity: 0, scale: 0.94, y: -3 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96, y: -2 }}
      transition={{ duration: reducedMotion ? 0.12 : 0.4, ease: EASE }}
    >
      <IntelligenceGlow as="span" intensity="present" rounded="rounded-lg" active={active} wash>
        <span className="relative inline-flex flex-col p-1 rounded-lg border-2 border-fk-blue/40 bg-blue-50/40">
          <span className="mb-0.5 inline-flex items-center gap-1 self-start rounded-md bg-fk-blue/90 px-1.5 py-0.5 text-[9px] font-bold text-white uppercase tracking-wider shadow-sm">
            ✨ AI Intervention
          </span>
          {children}
        </span>
      </IntelligenceGlow>
      <motion.span
        className="mt-1 flex h-5 max-w-[340px] items-center gap-1.5 overflow-hidden text-fk-xs font-semibold text-fk-blue-dark"
        initial={reducedMotion ? false : { opacity: 0, y: -2 }}
        animate={{ opacity: active ? 1 : 0, y: active ? 0 : -2 }}
        transition={{ duration: reducedMotion ? 0.12 : 0.45, ease: EASE, delay: reducedMotion ? 0 : 0.08 }}
      >
        <Sparkles className="h-3 w-3 shrink-0 text-fk-blue animate-pulse" />
        <span className="truncate">{reasonText}</span>
        {actionLabel && onAction && (
          <button
            type="button"
            onClick={onAction}
            className="shrink-0 font-bold text-fk-blue hover:underline bg-fk-blue/10 px-1.5 py-0.5 rounded text-[11px] transition-transform hover:scale-105 active:scale-95"
          >
            {actionLabel} →
          </button>
        )}
      </motion.span>
    </motion.span>
  );
}

