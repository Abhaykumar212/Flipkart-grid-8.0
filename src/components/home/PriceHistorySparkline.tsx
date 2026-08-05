import type { PricePoint } from "../../types/product";

const WIDTH = 100;
const HEIGHT = 32;
const PAD = 3;

/** Minimal inline trend line — no axes, no library, just "down and to the right." */
export function PriceHistorySparkline({ points }: { points: PricePoint[] }) {
  if (points.length < 2) return null;

  const prices = points.map((p) => p.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const coords = points.map((p, i) => {
    const x = PAD + (i / (points.length - 1)) * (WIDTH - PAD * 2);
    const y = HEIGHT - PAD - ((p.price - min) / range) * (HEIGHT - PAD * 2);
    return [x, y] as const;
  });

  const path = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [lastX, lastY] = coords[coords.length - 1];
  const areaPath = `${path} L${lastX.toFixed(1)},${HEIGHT} L${coords[0][0].toFixed(1)},${HEIGHT} Z`;

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-8 w-full" preserveAspectRatio="none" aria-hidden>
      <path d={areaPath} fill="rgba(56,142,60,0.12)" />
      <path d={path} fill="none" stroke="#388e3c" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lastX} cy={lastY} r="2.25" fill="#388e3c" />
    </svg>
  );
}
