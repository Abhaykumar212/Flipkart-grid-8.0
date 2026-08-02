import type { AuthorizedIntervention } from "../../context/InterventionContext";

export interface InterventionSurfaceProps {
  intervention: AuthorizedIntervention;
  onClick: () => void;
  onDismiss: () => void;
}
