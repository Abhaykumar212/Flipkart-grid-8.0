import { useState } from "react";
import { Link } from "react-router-dom";
import { Minus, Plus } from "lucide-react";
import type { Product } from "../../types/product";
import { PriceBlock } from "../ui/PriceBlock";
import { AssuredBadge } from "../ui/Badge";
import { formatDeliveryDate } from "../../lib/format";
import { useCart } from "../../context/CartContext";
import { useWishlist } from "../../context/WishlistContext";

const FALLBACK = "/fallback-product.svg";

interface CartLineItemProps {
  product: Product;
  quantity: number;
  variant?: string;
  /** Checkout renders these as a static list — no stepper, no remove/save actions. */
  readOnly?: boolean;
}

export function CartLineItem({ product, quantity, variant, readOnly = false }: CartLineItemProps) {
  const { updateQuantity, removeItem } = useCart();
  const { toggleWishlist, isWishlisted } = useWishlist();
  const [src, setSrc] = useState(product.images[0] ?? FALLBACK);
  const { price, delivery, badges } = product;

  return (
    <div className="bg-white p-4 sm:p-6" data-testid="cart-item">
      <div className="flex gap-4 sm:gap-6">
        <div className="flex w-[88px] shrink-0 flex-col items-center gap-3 sm:w-[100px]">
          <Link
            to={`/product/${product.slug}`}
            className="flex h-[100px] w-full items-center justify-center"
          >
            <img
              src={src}
              alt={product.title}
              loading="lazy"
              width="100"
              height="100"
              onError={() => setSrc(FALLBACK)}
              className="max-h-full max-w-full object-contain"
            />
          </Link>

          {readOnly ? (
            <span className="text-fk-base text-fk-muted" data-testid="cart-item-quantity">
              Qty: {quantity}
            </span>
          ) : (
            /* Quantity stepper */
            <div className="flex items-center gap-1">
              <button
                onClick={() => updateQuantity(product.id, quantity - 1, variant)}
                disabled={quantity <= 1}
                aria-label="Decrease quantity"
                className="flex h-10 w-10 items-center justify-center rounded-full border border-fk-border text-fk-ink disabled:cursor-not-allowed disabled:opacity-40 sm:h-9 sm:w-9"
              >
                <Minus className="h-3.5 w-3.5" strokeWidth={2.5} />
              </button>
              <span
                className="min-w-8 rounded-[2px] border border-fk-border px-1.5 py-0.5 text-center text-fk-base tabular-nums"
                data-testid="cart-item-quantity"
              >
                {quantity}
              </span>
              <button
                onClick={() => updateQuantity(product.id, quantity + 1, variant)}
                aria-label="Increase quantity"
                className="flex h-10 w-10 items-center justify-center rounded-full border border-fk-border text-fk-ink sm:h-9 sm:w-9"
              >
                <Plus className="h-3.5 w-3.5" strokeWidth={2.5} />
              </button>
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <Link to={`/product/${product.slug}`}>
            <h3 className="line-clamp-2 text-fk-md text-fk-ink hover:text-fk-blue">
              {product.title}
            </h3>
          </Link>

          <div className="mt-1 flex items-center gap-2 text-fk-sm text-fk-muted">
            <span>Seller: {product.seller?.name ?? "RetailNet"}</span>
            {badges.assured && <AssuredBadge />}
          </div>

          {variant && <p className="mt-1 text-fk-base font-medium text-fk-ink">{variant}</p>}

          <PriceBlock
            mrp={price.mrp}
            sellingPrice={price.sellingPrice}
            size="md"
            className="mt-2"
          />

          <p className="mt-2 text-fk-base text-fk-ink">
            Delivery by{" "}
            <span className="font-medium">
              {formatDeliveryDate(delivery.estimatedDays)}
            </span>
            {delivery.free && <span className="text-fk-green"> — Free</span>}
          </p>
        </div>
      </div>

      {!readOnly && (
        <div className="mt-4 flex flex-wrap items-center gap-x-6 pl-0 sm:pl-[124px]">
          <button
            onClick={() => {
              if (!isWishlisted(product.id)) toggleWishlist(product.id);
              removeItem(product.id, variant);
            }}
            className="min-h-11 text-fk-md font-medium uppercase text-fk-ink hover:text-fk-blue"
          >
            Save for later
          </button>
          <button
            onClick={() => removeItem(product.id, variant)}
            className="min-h-11 text-fk-md font-medium uppercase text-fk-ink hover:text-fk-blue"
            data-testid="cart-item-remove"
          >
            Remove
          </button>
        </div>
      )}
    </div>
  );
}
