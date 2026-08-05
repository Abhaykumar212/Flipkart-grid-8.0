import { useEffect, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
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
import { SocialProof } from "../components/pdp/SocialProof";
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
import { isLowestPriceInDays } from "../lib/priceHistory";
import { useBrowsingAgentTrigger } from "../components/intervention/BrowsingAgentCard";

export default function ProductDetail() {
  const { slug } = useParams<{ slug: string }>();
  const product = slug ? productBySlug.get(slug) : undefined;
  const navigate = useNavigate();
  const { recordPincodeCheck, recordProductVisit } = useTracker();
  const { has, toggle } = useWishlist();
  const [pincode, setPincode] = useState("");
  const { trigger: triggerBrowsingAgent, node: browsingAgentCard } = useBrowsingAgentTrigger();

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
      triggerBrowsingAgent({
        type: "product_view",
        productId: product.id,
        productName: product.title,
        price: product.price.sellingPrice,
        category: product.category,
      });
    }

    const handleMouseLeave = (e: MouseEvent) => {
      if (e.clientY <= 10) {
        pageContext.markReviewDwell(product?.id || "");
      }
    };
    document.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      pageContext.setCurrentProduct(null);
      document.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [product?.id, triggerBrowsingAgent]);

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
  const isLowestPrice = isLowestPriceInDays(priceHistory, price.sellingPrice, 90);
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

  const descRef = useRef<HTMLDivElement>(null);
  const [showDescTakeaways, setShowDescTakeaways] = useState(false);
  const sessionViews = userHistory.getSnapshot().recentViewProductIds;
  const showComparison = compareProducts.length > 0 && sessionViews.length >= 2;

  useEffect(() => {
    const el = descRef.current;
    if (!el) return;
    let timer: number | null = null;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          timer = window.setTimeout(() => {
            setShowDescTakeaways(true);
          }, 1500);
        } else if (timer !== null) {
          window.clearTimeout(timer);
          timer = null;
        }
      },
      { threshold: 0.3 },
    );
    observer.observe(el);
    return () => {
      observer.disconnect();
      if (timer !== null) window.clearTimeout(timer);
    };
  }, [product?.id]);

  return (
    <div className="flex flex-col gap-3">
      {browsingAgentCard}
      {/* Breadcrumb Navigation */}
      <ProductBreadcrumb
        category={product.category}
        subCategory={product.subCategory}
        title={product.title}
      />

      {/* Main Product Section */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[2fr_3fr]">
        <ImageGallery
          product={product}
          seller={seller}
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

          <AnimatePresence mode="wait" initial={false}>
            {priceInline.isActive && priceContent ? (
              <InlineHighlight key="highlighted" {...priceContent}>
                {priceBlock}
              </InlineHighlight>
            ) : (
              <span key="plain">{priceBlock}</span>
            )}
          </AnimatePresence>
          {isLowestPrice && (
            <span
              className="mt-2 inline-flex rounded-[2px] bg-fk-green/10 px-2 py-1 text-fk-sm font-medium text-fk-green"
              data-testid="lowest-price-badge"
            >
              Lowest price in 90 days
            </span>
          )}

          {/* Social proof + Stock Urgency */}
          <div className="mt-3">
            <SocialProof productId={product.id} />
            <StockUrgency inStock={stock.inStock} quantityLeft={stock.quantityLeft} />
          </div>

          <div className="mt-4">
            <OffersList offers={offers} emi={emi} sellingPrice={price.sellingPrice} />
          </div>

          {/* EMI Calculator */}
          <div className="mt-4" id="emi-options">
            <EMICalculator sellingPrice={price.sellingPrice} emi={emi} />
          </div>

          <div className="mt-5 border-t border-fk-border pt-4" id="delivery-pincode">
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
            <AnimatePresence mode="wait" initial={false}>
              {deliveryInline.isActive && deliveryInline.content ? (
                <InlineHighlight key="highlighted" {...deliveryInline.content}>
                  {deliveryLine}
                </InlineHighlight>
              ) : (
                <div key="plain">{deliveryLine}</div>
              )}
            </AnimatePresence>
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

      <SpecificationsTable productId={product.id} sections={specifications} />

      <section ref={descRef} className="rounded-[2px] bg-white p-6">
        <h2 className="mb-2 text-fk-xl font-medium text-fk-ink">Product Description</h2>
        {showDescTakeaways && (
          <div className="mb-4 rounded-2xl border-2 border-fk-blue/40 bg-gradient-to-r from-blue-50/90 to-indigo-50/90 p-4 shadow-md backdrop-blur-md animate-in fade-in slide-in-from-top-2 duration-500">
            <div className="mb-2 flex items-center justify-between">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 px-3 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white shadow-sm">
                ✨ AI Intervention: Summarized Key Takeaways
              </span>
              <span className="text-[11px] font-bold text-fk-blue">Pattern Dwell Triggered (1.5s)</span>
            </div>
            <p className="text-fk-sm font-semibold text-fk-ink">
              {product.title} combines flagship hardware with top-rated buyer feedback. Features {product.highlights.slice(0, 3).join(", ")}.
            </p>
            <div className="mt-2 flex flex-wrap gap-2 text-fk-xs">
              <span className="rounded-md bg-emerald-100 px-2 py-1 font-bold text-emerald-800">✓ 1-Year Brand Warranty</span>
              <span className="rounded-md bg-blue-100 px-2 py-1 font-bold text-blue-800">✓ 7-Day Replacement</span>
              <span className="rounded-md bg-purple-100 px-2 py-1 font-bold text-purple-800">✓ No-Cost EMI Eligible</span>
            </div>
          </div>
        )}
        <p className="text-fk-base text-fk-ink">{description}</p>
      </section>

      {/* Product Comparison Table — shown if user viewed multiple products in session */}
      {showComparison && (
        <section id="similar-products" className="relative rounded-2xl border-2 border-fk-blue/50 bg-white p-6 shadow-fk-glow animate-in fade-in duration-500">
          <div className="mb-3 flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 px-3 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white shadow-sm">
              ✨ AI Intervention: Intelligent Model Comparison
            </span>
            <span className="text-[11px] font-semibold text-fk-blue">Session history triggered ({sessionViews.length} products viewed)</span>
          </div>
          <ProductComparison products={compareProducts} currentProduct={product} />
        </section>
      )}

      {/* Questions & Answers */}
      <QuestionsAndAnswers
        productTitle={product.title}
        brand={product.brand}
        category={product.category}
      />

      <RatingsAndReviews
        productId={product.id}
        ratingDistribution={ratingDistribution}
        reviews={reviews}
        highlights={product.highlights}
      />

      {/* Related Product Rails */}
      <RelatedProductsRail product={product} />
    </div>
  );
}
