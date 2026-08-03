import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Heart } from "lucide-react";
import { productBySlug } from "../data/products";
import { formatDeliveryDate, formatINR } from "../lib/format";
import {
  getSpecifications,
  getDescription,
  getSeller,
  getRatingDistribution,
  getReviews,
} from "../lib/productDetails";
import { getCompareProducts } from "../lib/relatedProducts";
import { Button } from "../components/ui/Button";
import { RatingStars } from "../components/ui/RatingStars";
import { PriceBlock } from "../components/ui/PriceBlock";
import { ImageGallery } from "../components/pdp/ImageGallery";
import { SpecificationsTable } from "../components/pdp/SpecificationsTable";
import { RatingsAndReviews } from "../components/pdp/RatingsAndReviews";
import { OffersList } from "../components/pdp/OffersList";
import { ProductBreadcrumb } from "../components/pdp/ProductBreadcrumb";
import { StockUrgency } from "../components/pdp/StockUrgency";
import { EMICalculator } from "../components/pdp/EMICalculator";
import { SellerInfo } from "../components/pdp/SellerInfo";
import { ProductComparison } from "../components/pdp/ProductComparison";
import { QuestionsAndAnswers } from "../components/pdp/QuestionsAndAnswers";
import { RelatedProductsRail } from "../components/pdp/RelatedProductsRail";
import { useTracker } from "../context/TrackerContext";
import { useWishlist } from "../context/WishlistContext";
import { userHistory } from "../lib/userHistory";
import { pageContext } from "../lib/pageContext";
import { InlineHighlight } from "../components/intervention/InlineHighlight";
import { useInlineTarget } from "../components/intervention/useInlineTarget";

export default function ProductDetail() {
  const { slug } = useParams<{ slug: string }>();
  const product = slug ? productBySlug.get(slug) : undefined;
  const navigate = useNavigate();
  const { recordPincodeCheck, recordProductVisit } = useTracker();
  const { has, toggle } = useWishlist();
  const [pincode, setPincode] = useState("");

  useEffect(() => {
    if (product) {
      recordProductVisit(product.id);
      userHistory.recordView(product.id);
      pageContext.setCurrentProduct(product.id);
      pageContext.recordVisit({
        productId: product.id,
        title: product.title,
        brand: product.brand,
        category: product.category,
        price: product.price.sellingPrice,
      });
    }
    return () => pageContext.setCurrentProduct(null);
  }, [product?.id]);

  // Scroll to top on product change (when navigating between related products)
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [slug]);

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

  const { price, rating, offers, delivery, highlights, emi, stock } = product;

  // Every product renders full detail — hand-authored data wins where it
  // exists, everything else falls back to the deterministic generator so no
  // PDP in the 50-item catalog ever looks thin.
  const specifications = getSpecifications(product);
  const description = getDescription(product);
  const seller = getSeller(product);
  const ratingDistribution = getRatingDistribution(product);
  const reviews = getReviews(product);
  const totalRatings = ratingDistribution.reduce((sum, r) => sum + r.count, 0);
  const compareProducts = getCompareProducts(product);

  const priceInline = useInlineTarget("pdp-price-block");
  const deliveryInline = useInlineTarget("pdp-delivery");

  const priceBlock = (
    <span ref={priceInline.anchorRef} className="inline-block">
      <PriceBlock mrp={price.mrp} sellingPrice={price.sellingPrice} size="lg" className="mt-3" />
    </span>
  );

  // "with priceHistory context if the product has signals" — PriceBlock itself
  // takes no such prop, so the history summary is appended to the caption here,
  // where the product's `signals` are already in scope.
  const priceHistory = product.signals?.priceHistory;
  const priceContent =
    priceInline.isActive && priceInline.content && priceHistory && priceHistory.length > 0
      ? {
          ...priceInline.content,
          reasonText: `${priceInline.content.reasonText} Was ${formatINR(priceHistory[0].price)} on ${new Date(
            priceHistory[0].date,
          ).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}, now ${formatINR(
            priceHistory[priceHistory.length - 1].price,
          )}.`,
        }
      : priceInline.content;

  const deliveryLine = (
    <p ref={deliveryInline.anchorRef} className="mt-2 text-fk-base text-fk-ink">
      {delivery.free ? "Free delivery" : "Delivery charges apply"} — Delivery by{" "}
      <span className="font-medium">{formatDeliveryDate(delivery.estimatedDays)}</span>
    </p>
  );

  return (
    <div className="flex flex-col gap-3">
      {/* Breadcrumb Navigation */}
      <ProductBreadcrumb
        category={product.category}
        subCategory={product.subCategory}
        title={product.title}
      />

      {/* Main Product Section */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[2fr_3fr]">
        <ImageGallery
          productId={product.id}
          images={product.images}
          title={product.title}
        />

        <div className="rounded-[2px] bg-white p-6">
          <div className="flex items-start justify-between gap-3">
            <h1 className="line-clamp-2 text-fk-xl font-medium text-fk-ink">{product.title}</h1>
            <button
              type="button"
              onClick={() => toggle(product.id)}
              aria-label={has(product.id) ? "Remove from wishlist" : "Add to wishlist"}
              aria-pressed={has(product.id)}
              className="flex shrink-0 items-center gap-1.5 rounded-[2px] border border-fk-border px-3 py-1.5 text-fk-sm font-medium text-fk-ink hover:border-fk-flame"
            >
              <Heart
                className={`h-4 w-4 ${has(product.id) ? "fill-fk-flame text-fk-flame" : "text-fk-muted"}`}
                strokeWidth={2}
              />
              {has(product.id) ? "Wishlisted" : "Wishlist"}
            </button>
          </div>

          <div className="mt-2 flex items-center gap-3">
            <RatingStars variant="stars" value={rating.value} count={totalRatings} />
          </div>

          {priceInline.isActive && priceContent ? (
            <InlineHighlight {...priceContent}>{priceBlock}</InlineHighlight>
          ) : (
            priceBlock
          )}

          {/* Stock Urgency */}
          <div className="mt-3">
            <StockUrgency inStock={stock.inStock} quantityLeft={stock.quantityLeft} />
          </div>

          <div className="mt-4">
            <OffersList offers={offers} emi={emi} />
          </div>

          {/* EMI Calculator */}
          <div className="mt-4">
            <EMICalculator sellingPrice={price.sellingPrice} emi={emi} />
          </div>

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
            {deliveryInline.isActive && deliveryInline.content ? (
              <InlineHighlight {...deliveryInline.content}>{deliveryLine}</InlineHighlight>
            ) : (
              deliveryLine
            )}
          </div>

          {/* Expanded Seller Info */}
          <div className="mt-4 border-t border-fk-border pt-4">
            <SellerInfo seller={seller} delivery={delivery} />
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

      <SpecificationsTable sections={specifications} />

      <section className="rounded-[2px] bg-white p-6">
        <h2 className="mb-2 text-fk-xl font-medium text-fk-ink">Product Description</h2>
        <p className="text-fk-base text-fk-ink">{description}</p>
      </section>

      {/* Product Comparison Table */}
      {compareProducts.length > 0 && (
        <ProductComparison products={compareProducts} currentProduct={product} />
      )}

      {/* Questions & Answers */}
      <QuestionsAndAnswers
        productTitle={product.title}
        brand={product.brand}
        category={product.category}
      />

      <RatingsAndReviews productId={product.id} ratingDistribution={ratingDistribution} reviews={reviews} />

      {/* Related Product Rails */}
      <RelatedProductsRail product={product} />
    </div>
  );
}
