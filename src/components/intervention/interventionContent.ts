import type { RecommendedIntervention } from "../../lib/pipelineTrace";
import type { InterventionContentProps } from "./types";
import type { Language } from "../../context/LanguageContext";
import { translateHeadline, translateActionLabel, uiString } from "../../lib/interventionTranslations";

/**
 * Maps the backend-shaped `RecommendedIntervention` (lever_id, headline,
 * rationale, explanation[]) to the render-shaped `InterventionContentProps`
 * every surface primitive takes. `reasonText` is the one field every surface
 * always shows, so it's built from the strongest piece of backend evidence
 * (`explanation[0].observation`, itself built server-side from the SHAP
 * `observed_value — why_it_matters` pair) rather than the shorter `rationale`.
 *
 * Multilingual intervention system: `language` and `translatedRationale` are
 * optional so every existing call site keeps working untouched (defaults to
 * English, verbatim backend text). `translatedRationale` — the one field that
 * can be LLM-personalised per session and so can't come from the static
 * dictionary — is computed by the caller via `useTranslatedRationale` (a
 * hook, which this plain function can't call itself) and passed in.
 */
export function buildInterventionContent(
  active: RecommendedIntervention,
  onAction: () => void,
  onDismiss: () => void,
  language: Language = "en",
  translatedRationale?: string,
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
    title: translateHeadline(active.lever_id, active.headline, language),
    body: translatedRationale ?? active.rationale,
    reasonText: active.explanation[0]?.observation ?? uiString("aiSuggested", language),
    actionLabel: translateActionLabel(active.lever_id, actionLabel, language),
    onAction,
    onDismiss,
  };
}
