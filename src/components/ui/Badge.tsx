import { BadgeCheck } from "lucide-react";

interface AssuredBadgeProps {
  className?: string;
}

/** Flipkart Assured lockup — blue badge icon + italic wordmark. */
export function AssuredBadge({ className = "" }: AssuredBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-fk-xs font-medium text-fk-blue ${className}`}
    >
      <BadgeCheck className="h-3.5 w-3.5 text-fk-blue" strokeWidth={2.5} />
      <span className="italic">Assured</span>
    </span>
  );
}

interface DiscountBadgeProps {
  percent: number;
  className?: string;
}

export function DiscountBadge({ percent, className = "" }: DiscountBadgeProps) {
  if (percent <= 0) return null;
  return (
    <span className={`text-fk-base font-medium text-fk-green ${className}`}>
      {percent}% off
    </span>
  );
}

export function SponsoredBadge({ className = "" }: { className?: string }) {
  return (
    <span className={`text-fk-xs text-fk-muted ${className}`}>Sponsored</span>
  );
}

export function PlusBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-0.5 rounded-sm bg-fk-yellow px-1 text-fk-xs font-bold text-fk-ink ${className}`}
    >
      Plus
      <svg viewBox="0 0 24 24" className="h-2.5 w-2.5 fill-fk-blue">
        <path d="M12 2l2.4 7.2H22l-6.2 4.5 2.4 7.3L12 16.5l-6.2 4.5 2.4-7.3L2 9.2h7.6z" />
      </svg>
    </span>
  );
}
