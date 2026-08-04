import { useState } from "react";
import { Heart, Share2 } from "lucide-react";
import { Button } from "../ui/Button";
import { useCart } from "../../context/CartContext";
import { useIntervention } from "../../context/InterventionContext";
import { getAddToCartLabel } from "../../lib/pdpMicrocopy";
import type { Product, Seller } from "../../types/product";

const FALLBACK = "/fallback-product.svg";

interface ImageGalleryProps {
  product: Product;
  seller: Seller;
}

export function ImageGallery({ product, seller }: ImageGalleryProps) {
  const { id: productId, images, title } = product;
  const gallery = images.length > 0 ? images : [FALLBACK];
  const [activeIndex, setActiveIndex] = useState(0);
  const [mainSrc, setMainSrc] = useState(gallery[0]);
  const { addItem } = useCart();
  const { diagnosis } = useIntervention();
  const cause = diagnosis?.productId === productId
    ? diagnosis.analysis.primary_root_cause.category
    : null;

  const addToCartLabel = getAddToCartLabel(product, seller, cause);

  const select = (index: number) => {
    setActiveIndex(index);
    setMainSrc(gallery[index]);
  };

  return (
    <div className="rounded-[2px] bg-white p-4">
      <div className="relative flex gap-3">
        <div className="flex flex-col gap-2">
          {gallery.map((src, i) => (
            <button
              key={src + i}
              onClick={() => select(i)}
              aria-label={`Show image ${i + 1}`}
              aria-current={i === activeIndex}
              className={`flex h-14 w-14 items-center justify-center border p-1 ${
                i === activeIndex ? "border-2 border-fk-blue" : "border-fk-border"
              }`}
            >
              <img
                src={src}
                alt=""
                className="max-h-full max-w-full object-contain"
                onError={(e) => {
                  e.currentTarget.src = FALLBACK;
                }}
              />
            </button>
          ))}
        </div>

        <div className="relative flex h-[360px] flex-1 items-center justify-center">
          <img
            src={mainSrc}
            alt={title}
            className="max-h-full max-w-full object-contain"
            onError={() => setMainSrc(FALLBACK)}
          />

          <div className="absolute right-3 top-3 flex flex-col gap-2">
            <button
              aria-label="Add to wishlist"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-fk-muted shadow-fk-hover hover:text-fk-flame"
            >
              <Heart className="h-4.5 w-4.5" strokeWidth={2} />
            </button>
            <button
              aria-label="Share"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-fk-muted shadow-fk-hover hover:text-fk-blue"
            >
              <Share2 className="h-4.5 w-4.5" strokeWidth={2} />
            </button>
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-3">
        <Button
          variant="cart"
          className="w-full"
          data-testid="add-to-cart-button"
          onClick={() => addItem(productId)}
        >
          {addToCartLabel}
        </Button>
        {/* Buy Now stays inert until the checkout flow lands. */}
        <Button variant="buy" className="w-full" data-testid="buy-now-button">
          Buy Now
        </Button>
      </div>
    </div>
  );
}
