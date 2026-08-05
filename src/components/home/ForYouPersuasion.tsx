import { useEffect, useState, useSyncExternalStore } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { CheckCircle2, TrendingDown, Sparkles } from "lucide-react";
import { userHistory } from "../../lib/userHistory";
import { productById } from "../../data/products";
import { formatINR, discountPercent } from "../../lib/format";
import { getOrSynthesizePriceHistory, isLowestPriceInDays } from "../../lib/priceHistory";
import { PriceHistorySparkline } from "./PriceHistorySparkline";
import { RatingStars } from "../ui/RatingStars";
import type { Product } from "../../types/product";

const MAX_CARDS = 4;

/** One deterministic, product-specific reason to buy now — the instant fallback while the LLM pitch loads (or if it fails). */
function pitchLine(product: Product, isLowest: boolean): string {
  const pct = discountPercent(product.price.mrp, product.price.sellingPrice);
  if (isLowest) return "Lowest price in the last 90 days — it won't stay this low.";
  if (pct >= 40) return `${pct}% off right now — one of the steepest cuts in this category.`;
  if (product.rating.value >= 4.4 && product.rating.count >= 1000) {
    return `Rated ${product.rating.value.toFixed(1)}★ by ${product.rating.count.toLocaleString("en-IN")}+ buyers — a proven pick.`;
  }
  if (product.delivery.express) return "Eligible for express delivery — order today, unbox tomorrow.";
  return "Still in stock and matched to what you were just browsing.";
}

/** Session-lifetime cache — a product pitched once during this visit is never re-requested. */
const pitchCache = new Map<string, string[]>();

/** LLM-generated bullets, progressively replacing the deterministic one-liner once they arrive. Never blocks the card on network/LLM latency. */
function usePitchBullets(product: Product, isLowest: boolean): string[] | null {
  const [bullets, setBullets] = useState<string[] | null>(pitchCache.get(product.id) ?? null);

  useEffect(() => {
    if (pitchCache.has(product.id)) {
      setBullets(pitchCache.get(product.id) ?? null);
      return;
    }
    let cancelled = false;
    const pct = discountPercent(product.price.mrp, product.price.sellingPrice);
    fetch("http://localhost:8000/api/product-pitch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: product.title,
        category: product.category,
        price: product.price.sellingPrice,
        mrp: product.price.mrp,
        discount_pct: pct,
        rating: product.rating.value,
        rating_count: product.rating.count,
        is_lowest: isLowest,
      }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled || !data?.bullets?.length) return;
        pitchCache.set(product.id, data.bullets);
        setBullets(data.bullets);
      })
      .catch(() => {
        // Deterministic pitchLine() already covers this card — silent is correct here.
      });
    return () => {
      cancelled = true;
    };
  }, [product.id]);

  return bullets;
}

function ForYouCard({ product, index }: { product: Product; index: number }) {
  const history = getOrSynthesizePriceHistory(
    product.id,
    product.price.sellingPrice,
    product.signals?.priceHistory,
  );
  const isLowest = isLowestPriceInDays(history, product.price.sellingPrice, 90);
  const pct = discountPercent(product.price.mrp, product.price.sellingPrice);
  const pros = [
    ...(product.badges.assured ? ["Flipkart Assured — quality checked"] : []),
    ...product.highlights.slice(0, 2),
  ].slice(0, 3);
  const llmBullets = usePitchBullets(product, isLowest);

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: index * 0.06 }}
      className="flex w-[240px] shrink-0 flex-col rounded-lg border border-fk-border bg-white p-3.5 transition-shadow hover:shadow-fk-hover"
    >
      <Link to={`/product/${product.slug}`} className="group flex flex-col">
        <div className="flex items-start gap-3">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-md bg-slate-50">
            <img
              src={product.images[0] ?? "/fallback-product.svg"}
              alt={product.title}
              className="max-h-full max-w-full object-contain"
            />
          </div>
          <div className="min-w-0">
            <h3 className="line-clamp-2 text-fk-sm font-medium text-fk-ink group-hover:text-fk-blue">
              {product.title}
            </h3>
            <div className="mt-1 flex items-center gap-1.5">
              <RatingStars value={product.rating.value} count={product.rating.count} />
            </div>
          </div>
        </div>

        <div className="mt-2.5 flex items-baseline gap-1.5">
          <span className="text-fk-md font-bold text-fk-ink">{formatINR(product.price.sellingPrice)}</span>
          {pct > 0 && (
            <>
              <span className="text-fk-xs text-fk-muted line-through">{formatINR(product.price.mrp)}</span>
              <span className="text-fk-xs font-medium text-fk-green">{pct}% off</span>
            </>
          )}
        </div>

        {isLowest && (
          <span className="mt-1.5 inline-flex w-fit items-center gap-1 rounded-[2px] bg-fk-green/10 px-1.5 py-0.5 text-[10px] font-semibold text-fk-green">
            <TrendingDown className="h-3 w-3" />
            Lowest price in 90 days
          </span>
        )}

        <div className="mt-2.5">
          <PriceHistorySparkline points={history} />
        </div>

        {pros.length > 0 && (
          <ul className="mt-2 flex flex-col gap-1">
            {pros.map((pro) => (
              <li key={pro} className="flex items-start gap-1.5 text-[11px] leading-4 text-fk-ink/75">
                <CheckCircle2 className="mt-[1px] h-3 w-3 shrink-0 text-fk-green" />
                <span className="line-clamp-1">{pro}</span>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-2.5 border-t border-fk-border pt-2 text-[11px] font-medium text-fk-blue-dark">
          {llmBullets ? (
            <ul className="flex flex-col gap-1">
              {llmBullets.map((bullet, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-fk-blue" />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p>{pitchLine(product, isLowest)}</p>
          )}
        </div>
      </Link>
    </motion.div>
  );
}

/**
 * "You were looking for these" — the home page's one personalized rail.
 * Reads `userHistory` (recently-viewed product ids) rather than a static
 * "top rated" slice, and each card actively argues for the purchase (price
 * trend, badges, a reason keyed to whichever signal is strongest for that
 * product) instead of just relisting it.
 */
export function ForYouPersuasion() {
  const snapshot = useSyncExternalStore(
    (listener) => userHistory.subscribe(listener),
    () => userHistory.getSnapshot(),
  );

  const products = snapshot.recentViewProductIds
    .map((id) => productById.get(id))
    .filter((p): p is Product => Boolean(p))
    .slice(0, MAX_CARDS);

  if (products.length === 0) return null;

  return (
    <section className="bg-white px-4 py-4 sm:px-6">
      <div className="mb-3 flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-fk-blue to-indigo-600 text-white">
          <Sparkles className="h-3.5 w-3.5" />
        </span>
        <div>
          <h2 className="text-fk-lg font-medium text-fk-ink">You were looking for these</h2>
          <p className="text-fk-xs text-fk-muted">Picked up right where you left off</p>
        </div>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-1">
        {products.map((product, index) => (
          <ForYouCard key={product.id} product={product} index={index} />
        ))}
      </div>
    </section>
  );
}
