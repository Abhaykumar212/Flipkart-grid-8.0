import { useEffect, useState } from "react";
import { Eye, Flame } from "lucide-react";

function hashUnit(id: string): number {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  return (hash % 1000) / 1000;
}

/** Small deterministic drift so the viewer count feels alive without a real presence channel. */
function viewerCount(productId: string, now: number): number {
  const base = 4 + Math.round(hashUnit(productId) * 34); // 4-38, stable per product
  const bucket = Math.floor(now / 15_000); // ticks every 15s
  const wobble = Math.round(Math.sin(bucket + hashUnit(productId) * 100) * 3);
  return Math.max(2, base + wobble);
}

function purchases24h(productId: string): number {
  return 8 + Math.round(hashUnit(productId + "buy") * 140);
}

/**
 * Rung-0 passive nudge, same spirit as `StockUrgency` — social proof rather
 * than inventory pressure. Ticks on a slow client-only timer so it reads as
 * "live" without a websocket the demo doesn't have.
 */
export function SocialProof({ productId }: { productId: string }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 15_000);
    return () => window.clearInterval(timer);
  }, []);

  const viewers = viewerCount(productId, now);
  const buys = purchases24h(productId);

  return (
    <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-fk-sm">
      <span className="flex items-center gap-1.5 text-fk-ink/70">
        <Eye className="h-3.5 w-3.5 text-fk-blue" />
        <span className="font-medium text-fk-ink">{viewers}</span> people viewing this right now
      </span>
      <span className="flex items-center gap-1.5 text-fk-ink/70">
        <Flame className="h-3.5 w-3.5 text-fk-flame" />
        Bought <span className="font-medium text-fk-ink">{buys}</span> times in the last 24 hours
      </span>
    </div>
  );
}
