import { formatINR, discountPercent } from "../../lib/format";

interface PriceBlockProps {
  mrp: number;
  sellingPrice: number;
  size?: "sm" | "md" | "lg";
  nowrap?: boolean;
  className?: string;
}

const priceSize: Record<NonNullable<PriceBlockProps["size"]>, string> = {
  sm: "text-fk-md",
  md: "text-fk-lg",
  lg: "text-fk-xl",
};

export function PriceBlock({ mrp, sellingPrice, size = "sm", nowrap = false, className = "" }: PriceBlockProps) {
  const pct = discountPercent(mrp, sellingPrice);
  return (
    <span className={`inline-flex items-baseline gap-1.5 tabular-nums ${nowrap ? "flex-nowrap whitespace-nowrap" : "flex-wrap"} ${className}`}>
      <span className={`font-medium text-fk-ink ${priceSize[size]}`}>
        {formatINR(sellingPrice)}
      </span>
      {pct > 0 && (
        <>
          <span className="text-fk-base text-fk-muted line-through">
            {formatINR(mrp)}
          </span>
          <span className="text-fk-base font-medium text-fk-green">{pct}% off</span>
        </>
      )}
    </span>
  );
}
