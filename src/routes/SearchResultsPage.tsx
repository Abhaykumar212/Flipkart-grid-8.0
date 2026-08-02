import { useSearchParams, useNavigate } from "react-router-dom";
import { SearchX } from "lucide-react";
import { products } from "../data/products";
import type { CategorySlug } from "../types/product";
import { Button } from "../components/ui/Button";
import { ProductCard } from "../components/home/ProductCard";

const VALID_CATEGORIES: CategorySlug[] = ["mobiles", "electronics", "audio", "appliances", "fashion"];

export default function SearchResultsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const q = (searchParams.get("q") ?? "").trim().toLowerCase();
  // Distinguish "no category filter at all" (plain text search) from
  // "clicked a category with no matching inventory" (Grocery, Furniture, ...)
  // — the param is present in the URL either way, only its validity differs.
  const hasCategoryFilter = searchParams.has("category");
  const categoryParam = searchParams.get("category");
  const label = searchParams.get("label");
  const category = VALID_CATEGORIES.includes(categoryParam as CategorySlug)
    ? (categoryParam as CategorySlug)
    : null;
  const isUnmappedCategory = hasCategoryFilter && category === null;

  let results = products;
  if (hasCategoryFilter) {
    results = category ? results.filter((p) => p.category === category) : [];
  }
  if (q) {
    results = results.filter((p) =>
      [p.title, p.brand, p.subCategory, p.category].some((field) =>
        field.toLowerCase().includes(q),
      ),
    );
  }

  const heading = q
    ? `Showing results for "${searchParams.get("q")}"`
    : label
      ? `Best of ${label}`
      : "All Products";

  return (
    <div className="flex flex-col gap-3">
      <div className="bg-white p-4">
        <h1 className="text-fk-lg font-medium text-fk-ink">{heading}</h1>
        <p className="mt-0.5 text-fk-sm text-fk-muted">
          {results.length} {results.length === 1 ? "result" : "results"} found
        </p>
      </div>

      {results.length === 0 ? (
        <div className="flex flex-col items-center gap-3 bg-white px-6 py-20 text-center">
          <SearchX className="h-16 w-16 text-fk-border" strokeWidth={1.5} />
          <h2 className="text-fk-lg font-medium text-fk-ink">
            {isUnmappedCategory
              ? `No products in ${label ?? "this category"} yet`
              : "No products found"}
          </h2>
          <p className="text-fk-base text-fk-muted">
            {isUnmappedCategory
              ? "We don't carry this category yet — check back soon!"
              : "Try searching for a different product, brand, or category."}
          </p>
          <Button variant="primary" className="mt-2" onClick={() => navigate("/")}>
            Back to Home
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 bg-white p-4 sm:grid-cols-3 lg:grid-cols-5">
          {results.map((product) => (
            <ProductCard key={product.id} product={product} fixedWidth={false} />
          ))}
        </div>
      )}
    </div>
  );
}
