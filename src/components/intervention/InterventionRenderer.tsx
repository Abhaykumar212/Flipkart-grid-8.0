import { useEffect } from "react";
import { useIntervention } from "../../context/InterventionContext";
import { CheckoutAssistPanel } from "./CheckoutAssistPanel";
import { ComparisonDrawer } from "./ComparisonDrawer";
import { InlineCartCard } from "./InlineCartCard";
import { NonBlockingBanner } from "./NonBlockingBanner";
import { customerExplanation } from "../../lib/interventionPresentation";

type Surface = "global" | "cart" | "checkout" | "pdp";

/**
 * Which channels each mount point is allowed to render.
 *
 * `INLINE_CARD` is claimed by both `cart` and `pdp` deliberately: only one of
 * those mounts exists at a time, and an inline card is the right shape on
 * either page.
 *
 * `ASSISTANT_PANEL` is absent on purpose. `CompanionWidget` delivers those
 * decisions into the persistent chat thread and fires their impression itself;
 * rendering one here too would show the shopper the same recommendation twice
 * and double-count it.
 */
const CHANNELS_BY_SURFACE: Record<Surface, readonly string[]> = {
  global: ["BANNER", "COMPARISON_DRAWER"],
  cart: ["INLINE_CARD"],
  checkout: ["CHECKOUT_PANEL"],
  pdp: ["INLINE_CARD"],
};

export function InterventionRenderer({ surface }: { surface: Surface }) {
  const { intervention, explanation, shown, click, dismiss } = useIntervention();
  const channel = intervention?.channel;
  const belongsHere = Boolean(
    intervention
    && intervention.decision_id
    && channel
    && CHANNELS_BY_SURFACE[surface].includes(channel)
  );

  useEffect(() => {
    if (belongsHere) shown(`${surface}:${channel}`);
  }, [belongsHere, channel, shown, surface]);

  if (!intervention || !intervention.decision_id || !belongsHere) return null;
  const props = {
    intervention,
    reasons: customerExplanation(explanation, intervention.reason),
    onClick: click,
    onDismiss: dismiss,
  };
  if (channel === "BANNER") return <NonBlockingBanner {...props} />;
  if (channel === "COMPARISON_DRAWER") return <ComparisonDrawer {...props} />;
  if (channel === "CHECKOUT_PANEL") return <CheckoutAssistPanel {...props} />;
  return <InlineCartCard {...props} />;
}
