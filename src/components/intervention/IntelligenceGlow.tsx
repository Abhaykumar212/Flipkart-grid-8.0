import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { useReducedMotion } from "./useReducedMotion";

type Intensity = "subtle" | "present";

interface IntelligenceGlowProps {
  intensity?: Intensity;
  /** Whether the glow/shimmer chrome is shown at all. Toggling this never resizes children. */
  active?: boolean;
  /** Adds a faint color wash behind the content itself, not just the ring — for content that has no background of its own (e.g. plain inline text) to keep the highlight from getting lost. */
  wash?: boolean;
  as?: "div" | "span";
  rounded?: string;
  className?: string;
  children: ReactNode;
}

const RING_INSET: Record<Intensity, string> = {
  subtle: "-inset-1.5",
  present: "-inset-2",
};

const RING_BLUR: Record<Intensity, string> = {
  subtle: "blur-[4px]",
  present: "blur-[6px]",
};

// [static opacity, breathing peak]
const RING_OPACITY: Record<Intensity, [number, number]> = {
  subtle: [0.55, 0.85],
  present: [0.55, 0.85],
};

const WASH =
  "linear-gradient(100deg, rgba(40,116,240,0.12), rgba(159,201,232,0.12) 55%, rgba(255,225,27,0.1))";

// fk-blue -> fk-cyan -> fk-yellow, low saturation, blue given the largest arc.
const GRADIENT =
  "conic-gradient(from 180deg, rgba(40,116,240,0.9), rgba(159,201,232,0.85) 35%, rgba(255,225,27,0.5) 62%, rgba(40,116,240,0.9) 100%)";

/**
 * Shared "intelligence layer" chrome: a breathing gradient border with a slow
 * shimmer sweep, frosted-glass adjacent. Glow/shimmer layers are absolutely
 * positioned overlays (negative inset, pointer-events-none) so they never
 * add to the box model — activating/deactivating never reflows children.
 */
export function IntelligenceGlow({
  intensity = "present",
  active = true,
  wash = false,
  as = "div",
  rounded = "rounded-2xl",
  className = "",
  children,
}: IntelligenceGlowProps) {
  const reducedMotion = useReducedMotion();
  const Wrapper = as;
  const [staticOpacity, peakOpacity] = RING_OPACITY[intensity];

  return (
    <Wrapper className={`relative ${as === "span" ? "inline-block" : ""} ${rounded} ${className}`}>
      {active && (
        <>
          <motion.span
            aria-hidden
            className={`pointer-events-none absolute ${RING_INSET[intensity]} rounded-[inherit] ${RING_BLUR[intensity]}`}
            style={{ background: GRADIENT, backgroundSize: "220% 220%" }}
            initial={false}
            animate={
              reducedMotion
                ? { opacity: staticOpacity }
                : {
                    opacity: [staticOpacity, peakOpacity, staticOpacity],
                    backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"],
                  }
            }
            transition={reducedMotion ? undefined : { duration: 6, ease: "easeInOut", repeat: Infinity }}
          />
          {!reducedMotion && (
            <span aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]">
              <motion.span
                className="absolute -left-1/3 inset-y-0 w-1/3"
                style={{ background: "linear-gradient(75deg, transparent, rgba(255,255,255,0.55), transparent)" }}
                animate={{ x: ["0%", "260%"] }}
                transition={{ duration: 3, ease: "easeInOut", repeat: Infinity, repeatDelay: 3 }}
              />
            </span>
          )}
          <span
            aria-hidden
            className="pointer-events-none absolute inset-0 rounded-[inherit] ring-1 ring-inset ring-white/50"
          />
          {wash && (
            <span
              aria-hidden
              className="pointer-events-none absolute inset-0 rounded-[inherit]"
              style={{ background: WASH }}
            />
          )}
        </>
      )}
      <span className={`relative ${as === "span" ? "inline-block" : "block"}`}>{children}</span>
    </Wrapper>
  );
}
