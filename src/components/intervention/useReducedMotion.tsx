import { createContext, useContext } from "react";
import { useReducedMotion as useFramerReducedMotion } from "framer-motion";

/**
 * null = no override, defer to system `prefers-reduced-motion`.
 * Set by the intervention-lab toggle so both states can be previewed
 * without touching OS settings.
 */
export const MotionOverrideContext = createContext<boolean | null>(null);

export function MotionPreferenceProvider({
  reduced,
  children,
}: {
  reduced: boolean | null;
  children: React.ReactNode;
}) {
  return <MotionOverrideContext.Provider value={reduced}>{children}</MotionOverrideContext.Provider>;
}

export function useReducedMotion(): boolean {
  const override = useContext(MotionOverrideContext);
  const system = useFramerReducedMotion();
  return override ?? Boolean(system);
}
