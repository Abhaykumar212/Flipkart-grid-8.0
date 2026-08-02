import { useEffect } from "react";
import { useIntervention } from "../../context/InterventionContext";
import { AssistantPanel } from "./AssistantPanel";
import { CheckoutAssistPanel } from "./CheckoutAssistPanel";
import { ComparisonDrawer } from "./ComparisonDrawer";
import { InlineCartCard } from "./InlineCartCard";
import { NonBlockingBanner } from "./NonBlockingBanner";

type Surface = "global" | "cart" | "checkout";

export function InterventionRenderer({ surface }: { surface: Surface }) {
  const { intervention, shown, click, dismiss } = useIntervention();
  const channel = intervention?.channel;
  const belongsHere = Boolean(
    intervention
    && intervention.decision_id
    && (
      (surface === "global" && channel && ["BANNER", "ASSISTANT_PANEL", "COMPARISON_DRAWER"].includes(channel))
      || (surface === "cart" && channel === "INLINE_CARD")
      || (surface === "checkout" && channel === "CHECKOUT_PANEL")
    )
  );

  useEffect(() => {
    if (belongsHere) shown(`${surface}:${channel}`);
  }, [belongsHere, channel, shown, surface]);

  if (!intervention || !intervention.decision_id || !belongsHere) return null;
  const props = { intervention, onClick: click, onDismiss: dismiss };
  if (channel === "BANNER") return <NonBlockingBanner {...props} />;
  if (channel === "ASSISTANT_PANEL") return <AssistantPanel {...props} />;
  if (channel === "COMPARISON_DRAWER") return <ComparisonDrawer {...props} />;
  if (channel === "CHECKOUT_PANEL") return <CheckoutAssistPanel {...props} />;
  return <InlineCartCard {...props} />;
}
