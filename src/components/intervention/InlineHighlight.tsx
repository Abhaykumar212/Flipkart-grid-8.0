import type { KeyboardEvent, ReactNode } from "react";
import { Sparkles } from "lucide-react";
import { IntelligenceGlow } from "./IntelligenceGlow";
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
  /* ── quiet variant ─────────────────────────────────────────────────── */
  if (variant === "quiet") {
    return (
      <span
        className="inline-flex items-start rounded-md font-semibold"
        style={{ background: "rgba(40,116,240,0.07)" }}
        role="note"
        aria-label={title ? `${title}: ${body ?? ""}` : undefined}
      >
        {children}
      </span>
    );
  }

  /* ── glow variant (original) ───────────────────────────────────────── */
  function handleKeyDown(event: KeyboardEvent<HTMLSpanElement>) {
    if (event.key === "Escape") onDismiss?.();
  }

  return (
    <span
      className="inline-flex flex-col items-start align-middle outline-none"
      tabIndex={0}
      role="note"
      aria-label={`${title}: ${body}. ${reasonText}`}
      onKeyDown={handleKeyDown}
    >
      <IntelligenceGlow as="span" intensity="present" rounded="rounded-lg" active={active} wash>
        <span className="relative inline-flex flex-col p-1 rounded-lg border-2 border-fk-blue/40 bg-blue-50/40">
          <span className="mb-0.5 inline-flex items-center gap-1 self-start rounded-md bg-fk-blue/90 px-1.5 py-0.5 text-[9px] font-bold text-white uppercase tracking-wider shadow-sm">
            ✨ AI Intervention
          </span>
          {children}
        </span>
      </IntelligenceGlow>
      <span
        className="mt-1 flex h-5 max-w-[340px] items-center gap-1.5 overflow-hidden text-fk-xs font-semibold text-fk-blue-dark transition-all duration-500 ease-out"
        style={{ opacity: active ? 1 : 0, transform: active ? "translateY(0)" : "translateY(-2px)" }}
      >
        <Sparkles className="h-3 w-3 shrink-0 text-fk-blue animate-pulse" />
        <span className="truncate">{reasonText}</span>
        {actionLabel && onAction && (
          <button
            type="button"
            onClick={onAction}
            className="shrink-0 font-bold text-fk-blue hover:underline bg-fk-blue/10 px-1.5 py-0.5 rounded text-[11px]"
          >
            {actionLabel} →
          </button>
        )}
      </span>
    </span>
  );
}

