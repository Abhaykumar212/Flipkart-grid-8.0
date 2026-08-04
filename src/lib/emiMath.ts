import type { Emi } from "../types/product";

/**
 * Threshold above which the EMI total is considered "meaningfully more" than
 * cash. 3 % was chosen to filter out trivially small rounding-level
 * differences while still surfacing any real cost premium the shopper would
 * care about.
 */
const MEANINGFUL_THRESHOLD = 0.03;

export interface EmiComparison {
  /** The total paid over the full EMI term (monthly × months). */
  emiTotal: number;
  /** Cash (selling) price for comparison. */
  cashPrice: number;
  /** Absolute difference: emiTotal − cashPrice. Negative means EMI is cheaper (unusual but possible). */
  difference: number;
  /** difference / cashPrice — the relative overpay. */
  overPayRatio: number;
  /** True when emiTotal exceeds cashPrice by more than MEANINGFUL_THRESHOLD. */
  isMeaningfullyMore: boolean;
}

/**
 * Pure comparison of total cost of ownership: cash price vs EMI plan.
 *
 * Returns `null` when there is no EMI data to compare.
 *
 * The comparison is intentionally neutral — it only reports whether EMI costs
 * more, without nudging toward either payment method.
 */
export function compareEmiToCash(
  sellingPrice: number,
  emi: Emi | undefined,
): EmiComparison | null {
  if (!emi) return null;

  const emiTotal = emi.monthly * emi.months;
  const difference = emiTotal - sellingPrice;
  const overPayRatio = sellingPrice > 0 ? difference / sellingPrice : 0;

  return {
    emiTotal,
    cashPrice: sellingPrice,
    difference,
    overPayRatio,
    isMeaningfullyMore: overPayRatio > MEANINGFUL_THRESHOLD,
  };
}
