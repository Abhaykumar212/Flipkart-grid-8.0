import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Tag } from "lucide-react";
import { productBySlug } from "../data/products";
import { formatDeliveryDate } from "../lib/format";
import { Button } from "../components/ui/Button";
import { RatingStars } from "../components/ui/RatingStars";
import { PriceBlock } from "../components/ui/PriceBlock";
import { ImageGallery } from "../components/pdp/ImageGallery";
import { SpecificationsTable } from "../components/pdp/SpecificationsTable";
import { RatingsAndReviews } from "../components/pdp/RatingsAndReviews";
import { useTracker } from "../context/TrackerContext";

const FALLBACK_SELLER = { name: "RetailNet", rating: 4.0 };

export default function ProductDetail() {
  const { slug } = useParams<{ slug: string }>();
  const product = slug ? productBySlug.get(slug) : undefined;
  const navigate = useNavigate();
  const { recordPincodeCheck, recordProductVisit } = useTracker();
  const [pincode, setPincode] = useState("");

  useEffect(() => {
    if (product) recordProductVisit(product.id);
  }, [product?.id]);

  if (!product) {
    return (
      <div className="rounded-[2px] bg-white p-10 text-center shadow-fk-card">
        <p className="text-fk-lg text-fk-ink">Product not found.</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate("/")}>
          Back to Home
        </Button>
      </div>
    );
  }

  const { price, rating, offers, delivery, highlights, seller } = product;
  const totalRatings =
    product.ratingDistribution?.reduce((sum, r) => sum + r.count, 0) ?? rating.count;
  const resolvedSeller = seller ?? FALLBACK_SELLER;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[2fr_3fr]">
        <ImageGallery
          productId={product.id}
          images={product.images}
          title={product.title}
        />

        <div className="rounded-[2px] bg-white p-6">
          <h1 className="line-clamp-2 text-fk-xl font-medium text-fk-ink">{product.title}</h1>

          <div className="mt-2 flex items-center gap-3">
            <RatingStars variant="stars" value={rating.value} count={totalRatings} />
          </div>

          <PriceBlock mrp={price.mrp} sellingPrice={price.sellingPrice} size="lg" className="mt-3" />

          {offers.length > 0 && (
            <div className="mt-4">
              <h2 className="text-fk-md font-medium text-fk-ink">Available offers</h2>
              <ul className="mt-2 flex flex-col gap-2">
                {offers.map((offer) => (
                  <li key={offer} className="flex items-start gap-2 text-fk-base text-fk-ink">
                    <Tag className="mt-0.5 h-4 w-4 shrink-0 text-fk-green" strokeWidth={2} />
                    <span>
                      {offer} <a href="#" className="text-fk-blue">T&amp;C</a>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-5 border-t border-fk-border pt-4">
            <h2 className="text-fk-md font-medium text-fk-ink">Delivery</h2>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                const normalized = pincode.trim();
                if (normalized) recordPincodeCheck(normalized);
              }}
              className="mt-2 flex max-w-xs items-center gap-2"
            >
              <input
                type="text"
                placeholder="Enter pincode"
                aria-label="Enter delivery pincode"
                value={pincode}
                onChange={(event) => setPincode(event.target.value)}
                className="h-9 flex-1 rounded-[2px] border border-fk-border px-3 text-fk-base focus:outline-none focus:border-fk-blue"
              />
              <Button type="submit" variant="outline" size="sm">
                Check
              </Button>
            </form>
            <p className="mt-2 text-fk-base text-fk-ink">
              {delivery.free ? "Free delivery" : "Delivery charges apply"} — Delivery by{" "}
              <span className="font-medium">{formatDeliveryDate(delivery.estimatedDays)}</span>
            </p>
          </div>

          <div className="mt-4 flex items-center gap-2 border-t border-fk-border pt-4 text-fk-base text-fk-ink">
            <span>
              Sold by <span className="font-medium">{resolvedSeller.name}</span>
            </span>
            <RatingStars variant="pill" size="sm" value={resolvedSeller.rating} />
          </div>

          {highlights.length > 0 && (
            <div className="mt-4 border-t border-fk-border pt-4">
              <h2 className="text-fk-md font-medium text-fk-ink">Highlights</h2>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-fk-base text-fk-ink">
                {highlights.map((h) => (
                  <li key={h}>{h}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {product.specifications && <SpecificationsTable sections={product.specifications} />}

      {product.description && (
        <section className="rounded-[2px] bg-white p-6">
          <h2 className="mb-2 text-fk-xl font-medium text-fk-ink">Product Description</h2>
          <p className="text-fk-base text-fk-ink">{product.description}</p>
        </section>
      )}

      {product.reviews && product.ratingDistribution && (
        <RatingsAndReviews
          ratingDistribution={product.ratingDistribution}
          reviews={product.reviews}
        />
      )}
    </div>
  );
}
