import type { PricePoint } from "../types/product";

const DAY_MS = 24 * 60 * 60 * 1_000;

function validPoints(points: PricePoint[]): Array<PricePoint & { timestamp: number }> {
  return points.flatMap((point) => {
    const timestamp = Date.parse(point.date);
    return Number.isFinite(timestamp) && Number.isFinite(point.price) && point.price >= 0
      ? [{ ...point, timestamp }]
      : [];
  });
}

/** True only when data inside the requested window proves the current price is the minimum. */
export function isLowestPriceInDays(
  priceHistory: PricePoint[] | undefined,
  sellingPrice: number,
  days = 90,
  now = Date.now(),
): boolean {
  if (!priceHistory?.length || !Number.isFinite(sellingPrice) || days <= 0) return false;
  const cutoff = now - days * DAY_MS;
  const prices = validPoints(priceHistory)
    .filter((point) => point.timestamp >= cutoff && point.timestamp <= now)
    .map((point) => point.price);
  return prices.length > 0 && sellingPrice <= Math.min(...prices);
}

/**
 * Mirrors the existing tracker/price-drop lever: the newest recorded price is
 * a recent drop when it is lower than the preceding record and happened in the
 * configured recent window.
 */
export function hasRecentPriceDrop(
  priceHistory: PricePoint[] | undefined,
  sellingPrice: number,
  days = 7,
  now = Date.now(),
): boolean {
  if (!priceHistory || priceHistory.length < 2 || days <= 0) return false;
  const points = validPoints(priceHistory)
    .filter((point) => point.timestamp <= now)
    .sort((left, right) => left.timestamp - right.timestamp);
  const latest = points.at(-1);
  const previous = points.at(-2);
  if (!latest || !previous || now - latest.timestamp > days * DAY_MS) return false;
  return latest.price < previous.price && sellingPrice <= latest.price;
}
