import { Star } from "lucide-react";
import { formatIndianNumber } from "../../lib/format";

interface RatingStarsProps {
  value: number;
  count?: number;
  variant?: "pill" | "stars";
  size?: "sm" | "md";
  className?: string;
}

/**
 * "pill" — the green `4.4 ★` badge used on cards, with an optional muted
 * rating-count next to it (how Flipkart actually renders it in listings).
 * "stars" — a full 5-star row for the PDP.
 */
export function RatingStars({
  value,
  count,
  variant = "pill",
  size = "sm",
  className = "",
}: RatingStarsProps) {
  if (variant === "stars") {
    const rounded = Math.round(value);
    return (
      <span className={`inline-flex items-center gap-0.5 ${className}`}>
        {Array.from({ length: 5 }).map((_, i) => (
          <Star
            key={i}
            className={`h-4 w-4 ${
              i < rounded ? "fill-fk-green text-fk-green" : "fill-none text-fk-border"
            }`}
          />
        ))}
        {count !== undefined && (
          <span className="ml-1.5 text-fk-sm text-fk-muted">
            ({formatIndianNumber(count)})
          </span>
        )}
      </span>
    );
  }

  const padding = size === "sm" ? "px-1.5 py-0.5 text-fk-xs" : "px-2 py-0.5 text-fk-sm";

  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap ${className}`}>
      <span
        className={`inline-flex items-center gap-0.5 rounded-[2px] bg-fk-green font-medium text-white ${padding}`}
      >
        {value.toFixed(1)}
        <Star className="h-2.5 w-2.5 fill-white text-white" />
      </span>
      {count !== undefined && (
        <span className="min-w-0 truncate text-fk-xs text-fk-muted tabular-nums">
          ({formatIndianNumber(count)})
        </span>
      )}
    </span>
  );
}
