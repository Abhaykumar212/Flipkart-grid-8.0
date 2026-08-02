import { useState } from "react";
import { Link } from "react-router-dom";
import { Heart } from "lucide-react";
import type { Product } from "../../types/product";
import { RatingStars } from "../ui/RatingStars";
import { PriceBlock } from "../ui/PriceBlock";
import { AssuredBadge, SponsoredBadge } from "../ui/Badge";
import { useWishlist } from "../../context/WishlistContext";

const FALLBACK = "/fallback-product.svg";

interface ProductCardProps {
  product: Product;
  /** Rail cards are fixed-width; grid cards stretch. */
  fixedWidth?: boolean;
}

export function ProductCard({ product, fixedWidth = true }: ProductCardProps) {
  const [src, setSrc] = useState(product.images[0] ?? FALLBACK);
  const { price, rating, badges, stock, delivery } = product;
  const { has, toggle } = useWishlist();
  const wishlisted = has(product.id);

  return (
    <Link
      to={`/product/${product.slug}`}
      className={`group relative flex shrink-0 flex-col rounded-[2px] bg-white p-3 transition-shadow hover:shadow-fk-hover ${
        fixedWidth ? "w-[186px]" : "w-full"
      }`}
    >
      <button
        type="button"
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          toggle(product.id);
        }}
        aria-label={wishlisted ? "Remove from wishlist" : "Add to wishlist"}
        aria-pressed={wishlisted}
        className="absolute right-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-white/90 shadow-sm transition hover:bg-white"
      >
        <Heart
          className={`h-4 w-4 ${wishlisted ? "fill-fk-flame text-fk-flame" : "text-fk-muted"}`}
          strokeWidth={2}
        />
      </button>

      <div className="mb-2.5 flex h-[152px] items-center justify-center px-2">
        <img
          src={src}
          alt={product.title}
          loading="lazy"
          onError={() => setSrc(FALLBACK)}
          className="max-h-full max-w-full object-contain transition-transform duration-200 group-hover:scale-105"
        />
      </div>

      {badges.sponsored && <SponsoredBadge className="mb-0.5" />}

      <h3 className="line-clamp-2 text-fk-base text-fk-ink group-hover:text-fk-blue">
        {product.title}
      </h3>

      <div className="mt-1.5 flex items-center gap-2">
        <RatingStars value={rating.value} count={rating.count} />
        {badges.assured && <AssuredBadge />}
      </div>

      <PriceBlock
        mrp={price.mrp}
        sellingPrice={price.sellingPrice}
        className="mt-1.5"
      />

      <p className="mt-1 text-fk-sm text-fk-muted">
        {!stock.inStock ? (
          <span className="font-medium text-fk-flame">Out of Stock</span>
        ) : delivery.express ? (
          <span className="text-fk-green">Delivery by tomorrow</span>
        ) : delivery.free ? (
          "Free delivery"
        ) : (
          `Delivery in ${delivery.estimatedDays} days`
        )}
      </p>
    </Link>
  );
}
