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
  return {
    title: active.headline,
    body: active.rationale,
    reasonText: active.explanation[0]?.observation ?? "Recommended for your session",
    actionLabel: "Got it",
    onAction,
    onDismiss,
  };
}
