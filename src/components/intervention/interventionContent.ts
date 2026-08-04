import type { RecommendedIntervention } from "../../lib/pipelineTrace";
import type { InterventionContentProps } from "./types";

/**
 * Maps the backend-shaped `RecommendedIntervention` (lever_id, headline,
 * rationale, explanation[]) to the render-shaped `InterventionContentProps`
 * every surface primitive takes. `reasonText` is the one field every surface
 * always shows, so it's built from the strongest piece of backend evidence
 * (`explanation[0].observation`, itself built server-side from the SHAP
 * `observed_value — why_it_matters` pair) rather than the shorter `rationale`.
 */
export function buildInterventionContent(
  active: RecommendedIntervention,
  onAction: () => void,
  onDismiss: () => void,
): InterventionContentProps {
  let actionLabel = "Explore Offer";
  switch (active.lever_id) {
    case "emi_plan_highlight":
      actionLabel = "Explore EMI Plans";
      break;
    case "review_summary_surface":
      actionLabel = "Read AI Summary";
      break;
    case "free_delivery_waiver":
      actionLabel = "Apply Free Delivery";
      break;
    case "targeted_discount_code":
      actionLabel = "Claim Discount";
      break;
    case "delivery_speed_upgrade":
      actionLabel = "Upgrade Delivery";
      break;
    case "checkout_assist_chat":
    case "payment_retry_help":
      actionLabel = "Chat with AI Assistant";
      break;
    case "stock_scarcity_nudge":
      actionLabel = "View Similar Items";
      break;
    case "price_drop_alert":
      actionLabel = "View Price History";
      break;
    default:
      actionLabel = "Explore Feature";
  }

  return {
    title: active.headline,
    body: active.rationale,
    reasonText: active.explanation[0]?.observation ?? "✨ AI-suggested for your session",
    actionLabel,
    onAction,
    onDismiss,
  };
}
