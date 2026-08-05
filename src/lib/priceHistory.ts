import type { PricePoint } from "../types/product";
import { GENERATED_PRICE_HISTORY } from "../data/priceHistory.generated";

const DAY_MS = 24 * 60 * 60 * 1_000;

/** Deterministic 0-1 hash — only still used as a last-resort synthesis for a product missing from both sources. */
function hashUnit(id: string): number {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  return (hash % 1000) / 1000;
}

/**
 * Real per-product history, in priority order: hand-authored data on the
 * product itself, then `ml/generate_price_history.py`'s generated 90-day
 * daily dataset (`priceHistory.generated.ts` — regenerate it after changing
 * catalog prices), then — only for a product present in neither, which
 * shouldn't happen for the current catalog — a same-shape 4-point synthesis
 * so a chart still renders rather than nothing.
 */
export function getOrSynthesizePriceHistory(
  productId: string,
  sellingPrice: number,
  real: PricePoint[] | undefined,
  now = Date.now(),
): PricePoint[] {
  if (real && real.length >= 2) return real;

  const generated = GENERATED_PRICE_HISTORY[productId];
  if (generated && generated.length >= 2) return generated;

  const drift = 0.06 + hashUnit(productId) * 0.14; // 6%-20% higher 90 days ago
  const day = (offset: number) => new Date(now - offset * DAY_MS).toISOString().slice(0, 10);
  return [
    { date: day(90), price: Math.round(sellingPrice * (1 + drift)) },
    { date: day(45), price: Math.round(sellingPrice * (1 + drift * 0.55)) },
    { date: day(14), price: Math.round(sellingPrice * (1 + drift * 0.2)) },
    { date: day(0), price: sellingPrice },
  ];
}

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
