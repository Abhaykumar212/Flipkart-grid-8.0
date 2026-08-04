import { useRef, useState } from "react";
import { ChevronDown, GitCompareArrows } from "lucide-react";
import { Link } from "react-router-dom";
import type { Product } from "../../types/product";
import { discountPercent, formatINR } from "../../lib/format";
import { useSession } from "../../context/SessionContext";
import { RatingStars } from "../ui/RatingStars";

export function ProductComparison({ current, alternatives }: { current: Product; alternatives: Product[] }) {
  const [expanded, setExpanded] = useState(false);
  const emitted = useRef(false);
  const { emit } = useSession();
  const compared = [current, ...alternatives].slice(0, 4);
  if (compared.length < 2) return null;

  const toggle = () => {
    setExpanded((value) => !value);
    if (!emitted.current) {
      emitted.current = true;
      emit("PRODUCT_COMPARED", {
        productId: current.id,
        metadata: { compared_with: compared.slice(1).map((product) => product.id) },
      });
    }
  };

  return (
    <section className="rounded-[2px] bg-white p-4 sm:p-6" aria-labelledby="comparison-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="comparison-heading" className="text-fk-xl font-medium text-fk-ink">Compare similar products</h2>
          <p className="mt-1 text-fk-sm text-fk-muted">Price, rating, delivery, and listing highlights side by side.</p>
        </div>
        <button
          type="button"
          aria-expanded={expanded}
          onClick={toggle}
          className="inline-flex min-h-11 items-center gap-2 rounded-[2px] bg-fk-blue px-4 font-medium text-white"
        >
          <GitCompareArrows className="h-4 w-4" aria-hidden="true" />
          {expanded ? "Hide comparison" : `Compare ${compared.length} items`}
          <ChevronDown className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`} aria-hidden="true" />
        </button>
      </div>

      {expanded && (
        <div className="mt-5 overflow-x-auto" data-testid="product-comparison-table">
          <table className="w-full min-w-[760px] border-collapse text-left text-fk-sm">
            <thead>
              <tr>
                <th className="w-28 border-b border-fk-border p-3 text-fk-muted">Product</th>
                {compared.map((product, index) => (
                  <th key={product.id} className={`w-52 border-b border-fk-border p-3 align-top ${index === 0 ? "bg-blue-50" : ""}`}>
                    <Link to={`/product/${product.slug}`} className="group block text-center">
                      <img src={product.images[0]} alt="" className="mx-auto h-24 w-24 object-contain" />
                      <span className="mt-2 line-clamp-2 text-fk-base font-medium text-fk-ink group-hover:text-fk-blue">{product.title}</span>
                      {index === 0 && <span className="mt-1 block text-fk-xs text-fk-blue">Current item</span>}
                    </Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <th className="border-b border-fk-border p-3 text-fk-muted">Price</th>
                {compared.map((product, index) => (
                  <td key={product.id} className={`border-b border-fk-border p-3 text-center ${index === 0 ? "bg-blue-50" : ""}`}>
                    <strong className="text-fk-base text-fk-ink">{formatINR(product.price.sellingPrice)}</strong>
                    <span className="ml-2 text-fk-xs font-medium text-fk-green">{discountPercent(product.price.mrp, product.price.sellingPrice)}% off</span>
                  </td>
                ))}
              </tr>
              <tr>
                <th className="border-b border-fk-border p-3 text-fk-muted">Rating</th>
                {compared.map((product, index) => (
                  <td key={product.id} className={`border-b border-fk-border p-3 text-center ${index === 0 ? "bg-blue-50" : ""}`}>
                    <RatingStars value={product.rating.value} variant="pill" size="sm" />
                    <span className="ml-2 text-fk-xs text-fk-muted">{product.rating.count.toLocaleString("en-IN")}</span>
                  </td>
                ))}
              </tr>
              <tr>
                <th className="border-b border-fk-border p-3 align-top text-fk-muted">Highlights</th>
                {compared.map((product, index) => (
                  <td key={product.id} className={`border-b border-fk-border p-3 align-top ${index === 0 ? "bg-blue-50" : ""}`}>
                    <ul className="list-disc space-y-1 pl-4 text-fk-ink">
                      {product.highlights.slice(0, 3).map((highlight) => <li key={highlight}>{highlight}</li>)}
                    </ul>
                  </td>
                ))}
              </tr>
              <tr>
                <th className="p-3 text-fk-muted">Delivery</th>
                {compared.map((product, index) => (
                  <td key={product.id} className={`p-3 text-center text-fk-ink ${index === 0 ? "bg-blue-50" : ""}`}>
                    {product.stock.inStock ? `${product.delivery.estimatedDays} day${product.delivery.estimatedDays === 1 ? "" : "s"}` : "Out of stock"}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
