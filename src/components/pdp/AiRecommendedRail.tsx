import { useEffect, useState } from "react";
import { productById } from "../../data/products";
import { ProductRail } from "../home/ProductRail";
import type { Product } from "../../types/product";

interface Neighbour {
  product_id: string;
  score: number;
}

/**
 * Learned product recommendation model — content-based item-item cosine
 * similarity trained offline (`ml/train_recommender.py`), served from
 * `GET /api/recommendations/{id}`. A real (if simple) model fit from data,
 * not a hand-ranked "similar items" list.
 */
export function AiRecommendedRail({ productId }: { productId: string }) {
  const [neighbours, setNeighbours] = useState<Neighbour[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`http://localhost:8000/api/recommendations/${productId}?n=8`)
      .then((r) => r.json())
      .then((data) => {
        if (!cancelled) setNeighbours(data.recommendations ?? []);
      })
      .catch(() => !cancelled && setNeighbours([]));
    return () => {
      cancelled = true;
    };
  }, [productId]);

  if (!neighbours || neighbours.length === 0) return null;

  const products = neighbours
    .map((n) => productById.get(n.product_id))
    .filter((p): p is Product => Boolean(p));

  if (products.length === 0) return null;

  return (
    <ProductRail
      title="✨ AI-Recommended For You"
      subtitle="Content-based similarity model — ml/train_recommender.py"
      products={products}
    />
  );
}
