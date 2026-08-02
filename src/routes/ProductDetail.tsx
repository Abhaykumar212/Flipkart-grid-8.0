import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { RotateCcw, ShieldCheck, Truck } from "lucide-react";
import { productBySlug, products } from "../data/products";
import { formatDeliveryDate } from "../lib/format";
import {
  getSpecifications,
  getDescription,
  getSeller,
  getRatingDistribution,
  getReviews,
} from "../lib/productDetails";
import { Button } from "../components/ui/Button";
import { RatingStars } from "../components/ui/RatingStars";
import { PriceBlock } from "../components/ui/PriceBlock";
import { ImageGallery } from "../components/pdp/ImageGallery";
import { SpecificationsTable } from "../components/pdp/SpecificationsTable";
import { RatingsAndReviews } from "../components/pdp/RatingsAndReviews";
import { ProductRail } from "../components/home/ProductRail";
import { OffersList } from "../components/pdp/OffersList";
import { useTracker } from "../context/TrackerContext";
import { productVariantOptions } from "../lib/productPresentation";
import { categoryBySlug } from "../data/categories";

const FALLBACK_SELLER = { name: "RetailNet", rating: 4.2 };

export default function ProductDetail() {
  const { slug } = useParams<{ slug: string }>();
  const product = slug ? productBySlug.get(slug) : undefined;
  const navigate = useNavigate();
  const { recordPincodeCheck, recordProductVisit } = useTracker();
  const [pincode, setPincode] = useState("");
  const [pincodeMessage, setPincodeMessage] = useState("");
  const [selectedVariant, setSelectedVariant] = useState("");

  useEffect(() => {
    if (product) recordProductVisit(product.id);
    setSelectedVariant("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [product, recordProductVisit]);

  const variants = useMemo(() => product ? productVariantOptions(product) : [], [product]);

  if (!product) {
    return (
      <div className="rounded-[2px] bg-white p-10 text-center shadow-fk-card">
        <p className="text-fk-lg text-fk-ink">Product not found.</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate("/products")}>Browse Products</Button>
      </div>
    );
  }

  const { price, rating, offers, delivery, highlights, stock, emi } = product;
  const ratingDistribution = getRatingDistribution(product);
  const reviews = getReviews(product);
  const specifications = getSpecifications(product);
  const description = getDescription(product);
  const totalRatings = ratingDistribution.reduce((sum, item) => sum + item.count, 0);
  const resolvedSeller = getSeller(product) ?? FALLBACK_SELLER;
  const category = categoryBySlug.get(product.category);
  const related = products
    .filter((candidate) => candidate.id !== product.id && candidate.category === product.category)
    .sort((a, b) => Number(b.subCategory === product.subCategory) - Number(a.subCategory === product.subCategory) || b.rating.value - a.rating.value)
    .slice(0, 10);
  const schema = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.title,
    image: product.images,
    description,
    brand: { "@type": "Brand", name: product.brand },
    aggregateRating: { "@type": "AggregateRating", ratingValue: rating.value, reviewCount: rating.reviewCount },
    offers: { "@type": "Offer", priceCurrency: "INR", price: price.sellingPrice, availability: stock.inStock ? "https://schema.org/InStock" : "https://schema.org/OutOfStock" },
  };

  return (
    <div className="flex flex-col gap-3 pb-[calc(72px+env(safe-area-inset-bottom))] lg:pb-0">
      <script type="application/ld+json">{JSON.stringify(schema)}</script>
      <nav aria-label="Breadcrumb" className="px-1 text-fk-sm text-fk-muted">
        <Link to="/" className="hover:text-fk-blue">Home</Link><span aria-hidden="true"> / </span>
        <Link to={`/category/${product.category}`} className="hover:text-fk-blue">{category?.shortLabel}</Link><span aria-hidden="true"> / </span>
        <span className="line-clamp-1">{product.title}</span>
      </nav>

      <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[2fr_3fr]">
        <ImageGallery productId={product.id} images={product.images} title={product.title} selectedVariant={selectedVariant} variantRequired={variants.length > 0} inStock={stock.inStock} />

        <div className="rounded-[2px] bg-white p-4 sm:p-6">
          {product.badges.bestseller && <span className="mb-2 inline-block rounded-[2px] bg-fk-orange px-2 py-1 text-fk-xs font-medium text-white">Bestseller</span>}
          <h1 className="scroll-mt-28 text-balance text-fk-xl font-medium leading-7 text-fk-ink sm:text-xl">{product.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <RatingStars variant="stars" value={rating.value} count={totalRatings} />
            <a href="#ratings" className="text-fk-base font-medium text-fk-blue">{rating.reviewCount.toLocaleString("en-IN")} Reviews</a>
          </div>
          <p className="mt-3 text-fk-sm font-medium text-fk-green">Special price</p>
          <PriceBlock mrp={price.mrp} sellingPrice={price.sellingPrice} size="lg" className="mt-1" />

          <div className="mt-4">
            <OffersList offers={offers} emi={emi} />
          </div>

          {variants.length > 0 && (
            <fieldset className="mt-5 border-t border-fk-border pt-4">
              <legend className="text-fk-md font-medium text-fk-ink">Select Size</legend>
              <div className="mt-3 flex flex-wrap gap-2">
                {variants.map((variant) => <button type="button" key={variant} onClick={() => setSelectedVariant(variant)} aria-pressed={selectedVariant === variant} className={`h-11 min-w-11 rounded-[2px] border px-3 text-fk-md font-medium ${selectedVariant === variant ? "border-2 border-fk-blue text-fk-blue" : "border-fk-border text-fk-ink hover:border-fk-blue"}`}>{variant}</button>)}
              </div>
              {!selectedVariant && <p className="mt-2 text-fk-sm text-fk-muted">Choose a size before adding this item to your cart.</p>}
            </fieldset>
          )}

          <section className="mt-5 border-t border-fk-border pt-4" aria-labelledby="delivery-title">
            <h2 id="delivery-title" className="text-fk-md font-medium text-fk-ink">Delivery</h2>
            <form onSubmit={(event) => { event.preventDefault(); const normalized = pincode.trim(); if (/^\d{6}$/.test(normalized)) { recordPincodeCheck(normalized); setPincodeMessage(`Delivery available by ${formatDeliveryDate(delivery.estimatedDays)}`); } else setPincodeMessage("Enter a valid 6-digit pincode"); }} className="mt-2 flex max-w-sm items-center gap-2">
              <input type="text" inputMode="numeric" name="pincode" autoComplete="postal-code" maxLength={6} placeholder="Enter delivery pincode" aria-label="Enter delivery pincode" value={pincode} onChange={(event) => setPincode(event.target.value.replace(/\D/g, ""))} className="h-11 min-w-0 flex-1 rounded-[2px] border border-fk-border px-3 text-base focus:border-fk-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-fk-blue" />
              <Button type="submit" variant="outline" className="min-h-11" size="sm">Check</Button>
            </form>
            <p className={`mt-2 text-fk-base ${pincodeMessage.startsWith("Enter") ? "text-fk-flame" : "text-fk-green"}`} aria-live="polite">{pincodeMessage || `${delivery.free ? "Free delivery" : "Delivery charges apply"} · Delivery by ${formatDeliveryDate(delivery.estimatedDays)}`}</p>
          </section>

          <div className="mt-5 grid grid-cols-1 gap-3 border-y border-fk-border py-4 sm:grid-cols-3">
            <span className="flex items-center gap-2 text-fk-base text-fk-ink"><Truck className="h-5 w-5 text-fk-blue" />Fast tracked delivery</span>
            <span className="flex items-center gap-2 text-fk-base text-fk-ink"><RotateCcw className="h-5 w-5 text-fk-blue" />7-day replacement</span>
            <span className="flex items-center gap-2 text-fk-base text-fk-ink"><ShieldCheck className="h-5 w-5 text-fk-blue" />Secure payments</span>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2 text-fk-base text-fk-ink"><span>Sold by <span className="font-medium text-fk-blue">{resolvedSeller.name}</span></span><RatingStars variant="pill" size="sm" value={resolvedSeller.rating} /><span className={stock.quantityLeft <= 5 ? "text-fk-flame" : "text-fk-green"}>{stock.inStock ? (stock.quantityLeft <= 5 ? `Only ${stock.quantityLeft} left` : "In stock") : "Out of stock"}</span></div>

          {highlights.length > 0 && <section className="mt-4 border-t border-fk-border pt-4"><h2 className="text-fk-md font-medium text-fk-ink">Highlights</h2><ul className="mt-2 grid list-disc gap-1 pl-5 text-fk-base text-fk-ink sm:grid-cols-2">{highlights.map((highlight) => <li key={highlight}>{highlight}</li>)}</ul></section>}
        </div>
      </div>

      <SpecificationsTable sections={specifications} />
      <section className="rounded-[2px] bg-white p-4 sm:p-6"><h2 className="mb-2 text-fk-xl font-medium text-fk-ink">Product Description</h2><p className="max-w-4xl text-fk-base leading-6 text-fk-ink">{description}</p></section>
      <div id="ratings"><RatingsAndReviews ratingDistribution={ratingDistribution} reviews={reviews} /></div>
      {related.length > 0 && <ProductRail title="Similar Products" subtitle={`More in ${product.subCategory}`} products={related} viewAllHref={`/category/${product.category}`} />}
    </div>
  );
}
