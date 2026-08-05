import { useCallback, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { browsingAgent, type BrowsingCue, type BrowsingIntervention } from "../../lib/browsingAgent";
import { buildInterventionContent } from "./interventionContent";
import { AmbientCard } from "./AmbientCard";

const ACTION_TARGET: Record<string, string> = {
  scroll_to_emi: "emi-options",
  open_reviews: "customer-reviews",
  open_comparison: "customer-reviews",
  open_delivery: "delivery-pincode",
};

/**
 * Live wiring for the dedicated Browsing & Search Intent Agent
 * (`backend/agents/browsing_intent.py` + `lib/browsingAgent.ts`) — built
 * end-to-end on both ends but never actually called from any page. This is
 * that missing call site: `trigger(cue)` from wherever a real browsing
 * signal happens (a search, a product view), `node` renders whatever the
 * agent recommends.
 *
 * Deliberately its own small ambient surface, not routed through
 * `InterventionContext`'s policy engine — this agent doesn't touch the
 * fatigue budget or the delivery ledger, it's a separate, lighter-weight
 * signal path by original design.
 */
export function useBrowsingAgentTrigger() {
  const [result, setResult] = useState<BrowsingIntervention | null>(null);
  const lastCueKey = useRef<string | null>(null);

  const trigger = useCallback((cue: BrowsingCue) => {
    const key = `${cue.type}:${cue.query ?? cue.productId ?? ""}`;
    if (lastCueKey.current === key) return;
    lastCueKey.current = key;
    void browsingAgent.evaluateCueAsync(cue).then((next) => {
      if (next) setResult(next);
    });
  }, []);

  const dismiss = useCallback(() => setResult(null), []);

  const accept = useCallback(() => {
    const targetId = result?.actionType ? ACTION_TARGET[result.actionType] : undefined;
    if (targetId) document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth" });
    dismiss();
  }, [result, dismiss]);

  const node = (
    <AnimatePresence>
      {result && (
        <AmbientCard
          key={`${result.intervention.lever_id}-${lastCueKey.current}`}
          {...buildInterventionContent(result.intervention, accept, dismiss)}
        />
      )}
    </AnimatePresence>
  );

  return { trigger, node };
}
