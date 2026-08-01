import { formatINR, discountPercent } from "../../lib/format";

interface PriceBlockProps {
  mrp: number;
  sellingPrice: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const priceSize: Record<NonNullable<PriceBlockProps["size"]>, string> = {
  sm: "text-fk-md",
  md: "text-fk-lg",
  lg: "text-fk-xl",
};

export function PriceBlock({ mrp, sellingPrice, size = "sm", className = "" }: PriceBlockProps) {
  const pct = discountPercent(mrp, sellingPrice);
  return (
    <span className={`inline-flex flex-wrap items-baseline gap-1.5 ${className}`}>
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
