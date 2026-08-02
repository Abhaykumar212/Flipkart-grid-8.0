export interface InterventionContentProps {
  title: string;
  body: string;
  actionLabel?: string;
  onAction?: () => void;
  onDismiss: () => void;
  /** User-facing "why you're seeing this" line — always rendered, small + muted. */
  reasonText: string;
}
