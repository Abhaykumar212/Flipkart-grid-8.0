import type { KeyboardEvent, ReactNode } from "react";
import { Sparkles } from "lucide-react";
import { IntelligenceGlow } from "./IntelligenceGlow";
import type { InterventionContentProps } from "./types";

interface InlineHighlightProps extends InterventionContentProps {
  children: ReactNode;
  /** Drives the glow pulse + caption visibility. Space for the caption is always reserved, so toggling never reflows the page. */
  active?: boolean;
}

/**
 * Rung 0. Wraps an existing page element (a spec row, a price, a delivery
 * line) with a gentle glow + a small caption below. There's no room at this
 * scale for a heading or a real button: `title`/`body` become the
 * accessible label, the visible caption is always `reasonText`, and
 * `actionLabel` (if given) renders as an inline text-link next to it.
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
}: InlineHighlightProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLSpanElement>) {
    if (event.key === "Escape") onDismiss();
  }

  return (
    <span
      className="inline-flex flex-col items-start align-middle outline-none"
      tabIndex={0}
      role="note"
      aria-label={`${title}: ${body}. ${reasonText}`}
      onKeyDown={handleKeyDown}
    >
      <IntelligenceGlow as="span" intensity="subtle" rounded="rounded-md" active={active} wash>
        {children}
      </IntelligenceGlow>
      <span
        className="mt-1 flex h-4 max-w-[300px] items-center gap-1 overflow-hidden text-fk-xs font-medium text-fk-blue-dark transition-all duration-500 ease-out"
        style={{ opacity: active ? 1 : 0, transform: active ? "translateY(0)" : "translateY(-2px)" }}
      >
        <Sparkles className="h-2.5 w-2.5 shrink-0 text-fk-blue" />
        <span className="truncate">{reasonText}</span>
        {actionLabel && onAction && (
          <button
            type="button"
            onClick={onAction}
            className="shrink-0 font-semibold text-fk-blue hover:underline"
          >
            {actionLabel}
          </button>
        )}
      </span>
    </span>
  );
}
