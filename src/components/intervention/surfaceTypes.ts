import type { AuthorizedIntervention } from "../../context/InterventionContext";

export interface InterventionSurfaceProps {
  intervention: AuthorizedIntervention;
  reasons: string[];
  onClick: () => void;
  onDismiss: () => void;
}
