import { useIntervention } from "../../context/InterventionContext";
import { useLanguage } from "../../context/LanguageContext";
import { LEVER_TARGET_KEYS } from "../../lib/interventionTargets";
import { useTargetAnchor } from "../../lib/targetRegistry";
import { buildInterventionContent } from "./interventionContent";
import { useTranslatedRationale } from "./useTranslatedRationale";
import type { InterventionContentProps } from "./types";

export interface InlineTarget {
  /** Attach directly to the page element this key represents. */
  anchorRef: (el: HTMLElement | null) => void;
  /** Whether the active intervention is targeting this key right now. */
  isActive: boolean;
  content: InterventionContentProps | null;
  accept: () => void;
  dismiss: () => void;
}

/**
 * Used by the component that owns a specific inline anchor point (the PDP
 * delivery line, a `PriceBlock` call site, the EMI offer row, the reviews
 * header, ...). `anchorRef` always registers with the target registry,
 * independent of `isActive` — the registry needs to know an anchor exists on
 * the page whether or not anything is currently targeting it, so
 * `InterventionContext` can decide whether a lever's target is reachable at
 * selection time.
 *
 * Usage:
 *   const { anchorRef, isActive, content, accept, dismiss } = useInlineTarget("pdp-delivery");
 *   const line = <p ref={anchorRef}>...</p>;
 *   return isActive && content
 *     ? <InlineHighlight {...content} onAction={accept} onDismiss={dismiss}>{line}</InlineHighlight>
 *     : line;
 */
export function useInlineTarget(key: string): InlineTarget {
  const anchorRef = useTargetAnchor(key);
  const { active, surface, accept, dismiss } = useIntervention();
  const { language } = useLanguage();
  const translatedRationale = useTranslatedRationale(active?.lever_id ?? "", active?.rationale ?? "", language);

  const isActive =
    surface === "inline" && active != null && (LEVER_TARGET_KEYS[active.lever_id] ?? []).includes(key);

  const content =
    isActive && active ? buildInterventionContent(active, accept, dismiss, language, translatedRationale) : null;

  return { anchorRef, isActive, content, accept, dismiss };
}
