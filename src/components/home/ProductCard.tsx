import { useEffect, useRef, useState } from "react";
import { Heart, ShoppingCart } from "lucide-react";
import { Link } from "react-router-dom";
import type { Product } from "../../types/product";
import { RatingStars } from "../ui/RatingStars";
import { PriceBlock } from "../ui/PriceBlock";
import { AssuredBadge, SponsoredBadge } from "../ui/Badge";
import { useCart } from "../../context/CartContext";
import { useWishlist } from "../../context/WishlistContext";
import { productVariantOptions } from "../../lib/productPresentation";

const FALLBACK = "/fallback-product.svg";

interface ProductCardProps {
  product: Product;
  /** Rail cards are fixed-width; grid cards stretch. */
  fixedWidth?: boolean;
}

export function ProductCard({ product, fixedWidth = true }: ProductCardProps) {
  const [src, setSrc] = useState(product.images[0] ?? FALLBACK);
  const [added, setAdded] = useState(false);
  const resetTimer = useRef<number | null>(null);
  const { addItem } = useCart();
  const { isWishlisted, toggleWishlist } = useWishlist();
  const { price, rating, badges, stock, delivery } = product;
  const wishlisted = isWishlisted(product.id);
  const requiresOptions = productVariantOptions(product).length > 0;

  useEffect(() => () => {
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
  }, []);

  const addToCart = () => {
    addItem(product.id);
    setAdded(true);
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
    resetTimer.current = window.setTimeout(() => setAdded(false), 1600);
  };

  return (
    <article
      data-product-card
      className={`group relative flex shrink-0 snap-start flex-col overflow-hidden rounded-[2px] bg-white p-3 transition-shadow hover:z-10 hover:shadow-fk-hover ${fixedWidth ? "w-[196px] self-stretch" : "h-full w-full"}`}
    >
      <button
        type="button"
        onClick={() => toggleWishlist(product.id)}
        aria-label={wishlisted ? `Remove ${product.title} from wishlist` : `Add ${product.title} to wishlist`}
        aria-pressed={wishlisted}
        className={`absolute right-2 top-2 z-10 flex h-11 w-11 items-center justify-center rounded-full bg-white shadow-fk-card ${wishlisted ? "text-fk-flame" : "text-fk-muted hover:text-fk-flame"}`}
      >
        <Heart aria-hidden="true" className={`h-5 w-5 ${wishlisted ? "fill-current" : ""}`} strokeWidth={2} />
      </button>

      <Link to={`/product/${product.slug}`} className="mb-2.5 flex h-[164px] shrink-0 items-center justify-center px-2" aria-label={`View ${product.title}`}>
        <img src={src} alt={product.title} loading="lazy" width="164" height="164" onError={() => setSrc(FALLBACK)} className="max-h-full max-w-full object-contain transition-transform duration-200 group-hover:scale-105" />
      </Link>

      <div className="flex min-h-0 flex-1 flex-col">
        <div className="h-4 shrink-0 leading-4">
          {badges.sponsored ? <SponsoredBadge /> : <span aria-hidden="true">&nbsp;</span>}
        </div>
        <Link to={`/product/${product.slug}`} className="block h-9 shrink-0 min-w-0">
          <h3 className="line-clamp-2 h-9 text-fk-base text-fk-ink hover:text-fk-blue">{product.title}</h3>
        </Link>
        <div className="mt-1.5 flex h-6 shrink-0 items-center gap-1.5 overflow-hidden whitespace-nowrap">
          <RatingStars value={rating.value} count={rating.count} className="min-w-0 overflow-hidden" />
          {badges.assured && <AssuredBadge className="shrink-0" />}
        </div>
        <PriceBlock mrp={price.mrp} sellingPrice={price.sellingPrice} nowrap className="mt-1.5 min-h-5 shrink-0 overflow-hidden" />
        <p className="mt-1 h-5 shrink-0 truncate text-fk-sm leading-5 text-fk-muted">
          {!stock.inStock ? <span className="font-medium text-fk-flame">Out of Stock</span> : delivery.express ? <span className="text-fk-green">Delivery by tomorrow</span> : delivery.free ? "Free delivery" : `Delivery in ${delivery.estimatedDays} days`}
        </p>
        <div className="mt-auto pt-3">
          {requiresOptions ? (
            <Link data-card-action to={`/product/${product.slug}`} className="inline-flex min-h-11 w-full items-center justify-center rounded-[2px] border border-fk-blue px-3 text-fk-sm font-medium uppercase text-fk-blue hover:bg-blue-50">Choose Options</Link>
          ) : (
            <button data-card-action type="button" disabled={!stock.inStock} onClick={addToCart} className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[2px] bg-fk-orange px-3 text-fk-sm font-medium uppercase text-white hover:brightness-95 disabled:cursor-not-allowed disabled:bg-fk-border" aria-live="polite">
              <ShoppingCart aria-hidden="true" className="h-4 w-4" />
              {stock.inStock ? (added ? "Added" : "Add to Cart") : "Unavailable"}
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
