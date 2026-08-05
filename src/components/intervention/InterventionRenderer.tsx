import { AnimatePresence } from "framer-motion";
import { useIntervention } from "../../context/InterventionContext";
import { LEVER_TARGET_KEYS } from "../../lib/interventionTargets";
import { getAllMounted } from "../../lib/targetRegistry";
import { AmbientCard } from "./AmbientCard";
import { Spotlight } from "./Spotlight";
import { InterventionOutcomeCard } from "./InterventionOutcomeCard";
import { buildInterventionContent } from "./interventionContent";

/**
 * Dispatches the delivery layer's decision to a real surface component.
 *
 * `inline` is deliberately not handled here: `InlineHighlight` wraps the
 * target element as `children`, so only the page component that owns that
 * element can render it — see `useInlineTarget`. `companion` is also not
 * handled here: those levers are conversation-shaped and `CompanionWidget`
 * delivers them in the existing chat thread. This component only ever
 * renders `ambient` or `spotlight`, and only one of those at a time, since
 * `InterventionContext` holds at most one active intervention app-wide.
 */
export function InterventionRenderer() {
  const { active, surface, accept, dismiss, ctaOutcome, dismissOutcome } = useIntervention();

  const outcomeNode = (
    <AnimatePresence>
      {ctaOutcome && <InterventionOutcomeCard key={ctaOutcome.leverId} outcome={ctaOutcome} onDismiss={dismissOutcome} />}
    </AnimatePresence>
  );

  if (!active || !surface || surface === "inline" || surface === "companion") {
    return outcomeNode;
  }

  const content = buildInterventionContent(active, accept, dismiss);

  if (surface === "ambient") {
    return (
      <>
        <AmbientCard key={active.lever_id} {...content} />
        {outcomeNode}
      </>
    );
  }

  // surface === "spotlight" — target is guaranteed mounted at this point;
  // InterventionContext already downgraded to "ambient" otherwise.
  const targetEl = getAllMounted(LEVER_TARGET_KEYS[active.lever_id] ?? []);
  if (!targetEl) return outcomeNode;

  return (
    <>
      <Spotlight key={active.lever_id} targetRef={{ current: targetEl }} {...content} />
      {outcomeNode}
    </>
  );
}
