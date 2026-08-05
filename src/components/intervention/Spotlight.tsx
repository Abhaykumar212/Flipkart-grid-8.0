import { useCallback, useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { motion } from "framer-motion";
import { X } from "lucide-react";
import { IntelligenceGlow } from "./IntelligenceGlow";
import { useEscapeDismiss } from "./useEscapeDismiss";
import { useReducedMotion } from "./useReducedMotion";
import { FormattedText } from "../ui/FormattedText";
import type { InterventionContentProps } from "./types";

interface SpotlightProps extends InterventionContentProps {
  /** The existing page element to glow and anchor the callout beside. */
  targetRef: RefObject<HTMLElement | null>;
}

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

type Side = "right" | "left" | "below" | "above";

const GAP = 16;
const VIEWPORT_PAD = 16;
const CALLOUT_WIDTH = 320;
const FALLBACK_CALLOUT_HEIGHT = 170;

function rectFromDom(el: HTMLElement): Rect {
  const r = el.getBoundingClientRect();
  return { top: r.top, left: r.left, width: r.width, height: r.height };
}

function computeCalloutPosition(
  target: Rect,
  calloutSize: { width: number; height: number },
  viewport: { width: number; height: number },
): { top: number; left: number; side: Side } {
  const spaceRight = viewport.width - (target.left + target.width);
  const spaceLeft = target.left;
  const spaceBelow = viewport.height - (target.top + target.height);
  const spaceAbove = target.top;

  let side: Side;
  if (spaceRight >= calloutSize.width + GAP) side = "right";
  else if (spaceLeft >= calloutSize.width + GAP) side = "left";
  else if (spaceBelow >= calloutSize.height + GAP) side = "below";
  else if (spaceAbove >= calloutSize.height + GAP) side = "above";
  else side = spaceRight >= spaceLeft ? "right" : "left";

  let top: number;
  let left: number;
  if (side === "right" || side === "left") {
    top = target.top + target.height / 2 - calloutSize.height / 2;
    left = side === "right" ? target.left + target.width + GAP : target.left - calloutSize.width - GAP;
  } else {
    left = target.left + target.width / 2 - calloutSize.width / 2;
    top = side === "below" ? target.top + target.height + GAP : target.top - calloutSize.height - GAP;
  }

  top = Math.min(Math.max(top, VIEWPORT_PAD), viewport.height - calloutSize.height - VIEWPORT_PAD);
  left = Math.min(Math.max(left, VIEWPORT_PAD), viewport.width - calloutSize.width - VIEWPORT_PAD);

  return { top, left, side };
}

/**
 * Rung 2. Dims the page, glows the target element, anchors a frosted
 * callout beside it (falling back to left/below/above when the target sits
 * near a viewport edge). The target isn't rendered by this component — it
 * stays interactive by being lifted above the dim layer via z-index rather
 * than by punching a click-through hole in the overlay.
 */
export function Spotlight({ title, body, actionLabel, onAction, onDismiss, reasonText, targetRef }: SpotlightProps) {
  const reducedMotion = useReducedMotion();
  const calloutRef = useRef<HTMLDivElement>(null);
  const firstFocusableRef = useRef<HTMLButtonElement>(null);
  const [targetRect, setTargetRect] = useState<Rect | null>(null);
  const [calloutPos, setCalloutPos] = useState<{ top: number; left: number; side: Side } | null>(null);

  useEscapeDismiss(true, onDismiss);

  const recompute = useCallback(() => {
    const target = targetRef.current;
    if (!target) return;
    const rect = rectFromDom(target);
    setTargetRect(rect);
    const calloutEl = calloutRef.current;
    const size = calloutEl
      ? { width: calloutEl.offsetWidth, height: calloutEl.offsetHeight }
      : { width: Math.min(CALLOUT_WIDTH, window.innerWidth - VIEWPORT_PAD * 2), height: FALLBACK_CALLOUT_HEIGHT };
    setCalloutPos(computeCalloutPosition(rect, size, { width: window.innerWidth, height: window.innerHeight }));
  }, [targetRef]);

  useLayoutEffect(() => {
    recompute();
    const raf = requestAnimationFrame(recompute);
    window.addEventListener("resize", recompute);
    window.addEventListener("scroll", recompute, true);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", recompute);
      window.removeEventListener("scroll", recompute, true);
    };
  }, [recompute]);

  // Lift the target above the dim overlay via z-index instead of cutting a
  // hole in it, so the real element stays exactly as interactive as before.
  useEffect(() => {
    const target = targetRef.current;
    if (!target) return;
    const prevPosition = target.style.position;
    const prevZIndex = target.style.zIndex;
    if (getComputedStyle(target).position === "static") {
      target.style.position = "relative";
    }
    target.style.zIndex = "9996";
    return () => {
      target.style.position = prevPosition;
      target.style.zIndex = prevZIndex;
    };
  }, [targetRef]);

  const hasFocusedRef = useRef(false);
  useEffect(() => {
    if (hasFocusedRef.current || !calloutPos) return;
    hasFocusedRef.current = true;
    firstFocusableRef.current?.focus();
  }, [calloutPos]);

  if (!targetRect) return null;

  return (
    <>
      <motion.div
        className="fixed inset-0 z-[9995] bg-slate-900/35"
        onClick={onDismiss}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: reducedMotion ? 0.1 : 0.3 }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none fixed z-[9997]"
        initial={false}
        animate={{ top: targetRect.top - 6, left: targetRect.left - 6, width: targetRect.width + 12, height: targetRect.height + 12 }}
        transition={{ duration: reducedMotion ? 0 : 0.3, ease: "easeOut" }}
      >
        <IntelligenceGlow as="div" intensity="present" rounded="rounded-xl" className="h-full w-full">
          <div className="h-full w-full" />
        </IntelligenceGlow>
      </motion.div>
      <motion.div
        ref={calloutRef}
        role="dialog"
        aria-label={title}
        className="fixed z-[9998] w-[min(320px,calc(100vw-32px))]"
        initial={false}
        animate={calloutPos ? { top: calloutPos.top, left: calloutPos.left, opacity: 1 } : { opacity: 0 }}
        transition={{ duration: reducedMotion ? 0 : 0.3, ease: "easeOut" }}
      >
        <IntelligenceGlow intensity="present" rounded="rounded-2xl">
          <div className="relative rounded-2xl border border-white/60 bg-white/75 p-4 shadow-fk-glow backdrop-blur-xl">
            <button
              type="button"
              onClick={onDismiss}
              aria-label="Dismiss"
              className="absolute right-2.5 top-2.5 rounded-full p-1 text-fk-muted transition hover:bg-black/5 hover:text-fk-ink"
            >
              <X className="h-3.5 w-3.5" />
            </button>
            <h3 className="pr-5 text-fk-lg font-semibold text-fk-ink">{title}</h3>
            <FormattedText text={body} className="mt-1.5 text-fk-sm leading-5 text-fk-ink/80" />
            <p className="mt-2.5 text-fk-xs text-fk-muted">{reasonText}</p>
            <div className="mt-3.5 flex items-center gap-3">
              {actionLabel && onAction && (
                <button
                  ref={firstFocusableRef}
                  type="button"
                  onClick={onAction}
                  className="inline-flex items-center rounded-full bg-fk-blue px-4 py-1.5 text-fk-sm font-medium text-white transition hover:bg-fk-blue-dark"
                >
                  {actionLabel}
                </button>
              )}
              <button
                ref={actionLabel && onAction ? undefined : firstFocusableRef}
                type="button"
                onClick={onDismiss}
                className="text-fk-sm font-medium text-fk-muted hover:text-fk-ink"
              >
                Not now
              </button>
            </div>
          </div>
        </IntelligenceGlow>
      </motion.div>
    </>
  );
}
