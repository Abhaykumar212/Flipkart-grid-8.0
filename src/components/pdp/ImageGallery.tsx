import { useState } from "react";
import { Heart, Share2, ShoppingCart, Zap } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "../ui/Button";
import { useCart } from "../../context/CartContext";
import { useWishlist } from "../../context/WishlistContext";

const FALLBACK = "/fallback-product.svg";

interface ImageGalleryProps {
  productId: string;
  images: string[];
  title: string;
  selectedVariant?: string;
  variantRequired?: boolean;
  inStock?: boolean;
}

export function ImageGallery({
  productId,
  images,
  title,
  selectedVariant,
  variantRequired = false,
  inStock = true,
}: ImageGalleryProps) {
  const navigate = useNavigate();
  const gallery = images.length > 0 ? images : [FALLBACK];
  const [activeIndex, setActiveIndex] = useState(0);
  const [mainSrc, setMainSrc] = useState(gallery[0]);
  const [feedback, setFeedback] = useState("");
  const { addItem } = useCart();
  const { isWishlisted, toggleWishlist } = useWishlist();
  const wishlisted = isWishlisted(productId);
  const canAdd = inStock && (!variantRequired || Boolean(selectedVariant));

  const select = (index: number) => {
    setActiveIndex(index);
    setMainSrc(gallery[index]);
  };

  const add = () => {
    if (!canAdd) {
      setFeedback(variantRequired ? "Please select a size" : "This product is unavailable");
      return false;
    }
    addItem(productId, 1, selectedVariant ? `Size: ${selectedVariant}` : undefined);
    setFeedback("Added to cart");
    return true;
  };

  const share = async () => {
    try {
      let message = "Product link copied";
      if (navigator.share) {
        await navigator.share({ title, url: window.location.href });
        message = "Shared";
      } else {
        await navigator.clipboard.writeText(window.location.href);
      }
      setFeedback(message);
    } catch {
      // A cancelled native share sheet should not surface as an error.
    }
  };

  return (
    <div className="rounded-[2px] bg-white p-4 lg:sticky lg:top-20">
      <div className="relative flex flex-col gap-3 sm:flex-row">
        <div className="order-2 flex gap-2 overflow-x-auto overscroll-x-contain no-scrollbar sm:order-1 sm:flex-col sm:overflow-visible">
          {gallery.map((src, index) => (
            <button key={src + index} onClick={() => select(index)} aria-label={`Show image ${index + 1}`} aria-current={index === activeIndex} className={`flex h-14 w-14 items-center justify-center border p-1 ${index === activeIndex ? "border-2 border-fk-blue" : "border-fk-border"}`}>
              <img src={src} alt="" loading="lazy" width="56" height="56" className="max-h-full max-w-full object-contain" onError={(event) => { event.currentTarget.src = FALLBACK; }} />
            </button>
          ))}
        </div>

        <div className="relative order-1 flex h-[300px] min-w-0 flex-1 items-center justify-center sm:order-2 sm:h-[380px]">
          <img src={mainSrc} alt={title} width="416" height="416" className="max-h-full max-w-full object-contain" onError={() => setMainSrc(FALLBACK)} />
          <div className="absolute right-1 top-1 flex flex-col gap-2">
            <button onClick={() => toggleWishlist(productId)} aria-label={wishlisted ? "Remove from wishlist" : "Add to wishlist"} aria-pressed={wishlisted} className={`flex h-11 w-11 items-center justify-center rounded-full bg-white shadow-fk-hover ${wishlisted ? "text-fk-flame" : "text-fk-muted hover:text-fk-flame"}`}>
              <Heart aria-hidden="true" className={`h-5 w-5 ${wishlisted ? "fill-current" : ""}`} strokeWidth={2} />
            </button>
            <button onClick={share} aria-label="Share product" className="flex h-11 w-11 items-center justify-center rounded-full bg-white text-fk-muted shadow-fk-hover hover:text-fk-blue">
              <Share2 aria-hidden="true" className="h-5 w-5" strokeWidth={2} />
            </button>
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <Button variant="cart" className="min-h-12 w-full" data-testid="add-to-cart-button" onClick={add} disabled={!inStock}>
          <ShoppingCart className="h-4.5 w-4.5" /> Add to Cart
        </Button>
        <Button variant="buy" className="min-h-12 w-full" data-testid="buy-now-button" onClick={() => { if (add()) navigate("/checkout"); }} disabled={!inStock}>
          <Zap className="h-4.5 w-4.5 fill-current" /> Buy Now
        </Button>
      </div>
      <p className={`mt-2 min-h-5 text-center text-fk-sm ${feedback.includes("Please") || feedback.includes("unavailable") ? "text-fk-flame" : "text-fk-green"}`} aria-live="polite">{feedback}</p>
    </div>
  );
}
