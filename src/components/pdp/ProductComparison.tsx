import type { Product } from "../../types/product";
import { formatINR, discountPercent } from "../../lib/format";
import { RatingStars } from "../ui/RatingStars";
import { useCart } from "../../context/CartContext";
import { ShoppingCart } from "lucide-react";
import { Link } from "react-router-dom";

interface ProductComparisonProps {
  products: Product[];
  currentProduct: Product;
}

export function ProductComparison({ products, currentProduct }: ProductComparisonProps) {
  const { addItem } = useCart();
  const allProducts = [currentProduct, ...products].slice(0, 4);

  if (allProducts.length < 2) return null;

  return (
    <section className="rounded-[2px] bg-white p-6 shadow-fk-card">
      <h2 className="mb-6 text-fk-xl font-medium text-fk-ink">Compare with similar items</h2>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr>
              <th className="min-w-[100px] border-b border-fk-border p-4 text-fk-base font-medium text-fk-muted">
                Product
              </th>
              {allProducts.map((p, i) => (
                <th
                  key={p.id}
                  className={`min-w-[200px] w-[200px] border-b border-fk-border p-4 align-top ${
                    i === 0 ? "border-l-2 border-l-fk-blue bg-fk-blue/5" : ""
                  }`}
                >
                  <Link to={`/product/${p.slug}`} className="flex flex-col items-center group">
                    <img
                      src={p.images[0]}
                      alt={p.title}
                      className="mb-3 h-[140px] object-contain transition-transform group-hover:scale-105"
                    />
                    <h3 className="line-clamp-2 text-center text-fk-base font-medium text-fk-ink group-hover:text-fk-blue">
                      {p.title}
                    </h3>
                    {i === 0 && (
                      <span className="mt-1 text-fk-xs font-medium text-fk-blue">This item</span>
                    )}
                  </Link>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* Price Row */}
            <tr>
              <td className="border-b border-fk-border p-4 text-fk-base font-medium text-fk-muted">
                Price
              </td>
              {allProducts.map((p, i) => {
                const pct = discountPercent(p.price.mrp, p.price.sellingPrice);
                return (
                  <td
                    key={p.id}
                    className={`border-b border-fk-border p-4 ${
                      i === 0 ? "border-l-2 border-l-fk-blue bg-fk-blue/5" : ""
                    }`}
                  >
                    <div className="flex flex-col items-center gap-0.5">
                      <span className="text-fk-lg font-bold text-fk-ink">
                        {formatINR(p.price.sellingPrice)}
                      </span>
                      {pct > 0 && (
                        <div className="flex items-center gap-1.5 text-fk-sm">
                          <span className="text-fk-muted line-through">{formatINR(p.price.mrp)}</span>
                          <span className="font-medium text-fk-green">{pct}% off</span>
                        </div>
                      )}
                    </div>
                  </td>
                );
              })}
            </tr>

            {/* Rating Row */}
            <tr>
              <td className="border-b border-fk-border p-4 text-fk-base font-medium text-fk-muted">
                Rating
              </td>
              {allProducts.map((p, i) => (
                <td
                  key={p.id}
                  className={`border-b border-fk-border p-4 ${
                    i === 0 ? "border-l-2 border-l-fk-blue bg-fk-blue/5" : ""
                  }`}
                >
                  <div className="flex flex-col items-center gap-1">
                    <RatingStars value={p.rating.value} variant="pill" size="sm" />
                    <span className="text-fk-xs text-fk-muted">
                      ({p.rating.count.toLocaleString("en-IN")} ratings)
                    </span>
                  </div>
                </td>
              ))}
            </tr>

            {/* Highlights Row */}
            <tr>
              <td className="border-b border-fk-border p-4 align-top text-fk-base font-medium text-fk-muted">
                Highlights
              </td>
              {allProducts.map((p, i) => (
                <td
                  key={p.id}
                  className={`border-b border-fk-border p-4 align-top ${
                    i === 0 ? "border-l-2 border-l-fk-blue bg-fk-blue/5" : ""
                  }`}
                >
                  <ul className="list-disc space-y-1.5 pl-4 text-fk-sm text-fk-ink">
                    {p.highlights.slice(0, 3).map((h) => (
                      <li key={h}>{h}</li>
                    ))}
                  </ul>
                </td>
              ))}
            </tr>

            {/* Add to Cart Row */}
            <tr>
              <td className="p-4 text-fk-base font-medium text-fk-muted" />
              {allProducts.map((p, i) => (
                <td
                  key={p.id}
                  className={`p-4 ${i === 0 ? "border-l-2 border-l-fk-blue bg-fk-blue/5" : ""}`}
                >
                  <div className="flex justify-center">
                    <button
                      onClick={() => addItem(p.id)}
                      className="flex w-full items-center justify-center gap-2 rounded-[2px] bg-fk-orange px-4 py-2.5 text-fk-md font-medium uppercase text-white transition-colors hover:brightness-95"
                    >
                      <ShoppingCart className="h-4 w-4" />
                      Add to Cart
                    </button>
                  </div>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}
