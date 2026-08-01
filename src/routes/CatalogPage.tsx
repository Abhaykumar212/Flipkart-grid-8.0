import { useEffect, useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, SearchX, SlidersHorizontal, X } from "lucide-react";
import { ProductCard } from "../components/home/ProductCard";
import { catalogCategories, categoryBySlug } from "../data/categories";
import { products } from "../data/products";
import { discountPercent, formatIndianNumber } from "../lib/format";
import type { CategorySlug, Product } from "../types/product";

const PAGE_SIZE = 12;

type SortKey = "relevance" | "featured" | "price-asc" | "price-desc" | "rating" | "discount";

const priceRanges = [
  { id: "all", label: "Any price", min: 0, max: Number.POSITIVE_INFINITY },
  { id: "under-1000", label: "Under ₹1,000", min: 0, max: 999 },
  { id: "1000-10000", label: "₹1,000 – ₹10,000", min: 1000, max: 10000 },
  { id: "10000-50000", label: "₹10,000 – ₹50,000", min: 10000, max: 50000 },
  { id: "above-50000", label: "Above ₹50,000", min: 50001, max: Number.POSITIVE_INFINITY },
] as const;

function relevanceScore(product: Product, query: string): number {
  const normalized = query.toLowerCase();
  const title = product.title.toLowerCase();
  if (title === normalized) return 100;
  if (title.startsWith(normalized)) return 80;
  if (title.includes(normalized)) return 60;
  if (product.brand.toLowerCase().includes(normalized)) return 40;
  if (product.subCategory.toLowerCase().includes(normalized)) return 20;
  return 0;
}

export default function CatalogPage() {
  const { category: categoryParam } = useParams<{ category?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q")?.trim() ?? "";
  const brand = searchParams.get("brand") ?? "all";
  const price = searchParams.get("price") ?? "all";
  const sort = (searchParams.get("sort") as SortKey | null) ?? (query ? "relevance" : "featured");
  const inStockOnly = searchParams.get("stock") === "in";
  const page = Math.max(1, Number(searchParams.get("page")) || 1);
  const category = categoryBySlug.has(categoryParam as CategorySlug)
    ? (categoryParam as CategorySlug)
    : null;

  const updateParam = (key: string, value?: string) => {
    const next = new URLSearchParams(searchParams);
    if (!value || value === "all") next.delete(key);
    else next.set(key, value);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  const categoryProducts = useMemo(
    () => (category ? products.filter((product) => product.category === category) : products),
    [category],
  );

  const brands = useMemo(() => {
    const counts = new Map<string, number>();
    for (const product of categoryProducts) counts.set(product.brand, (counts.get(product.brand) ?? 0) + 1);
    return [...counts.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [categoryProducts]);

  const filtered = useMemo(() => {
    const normalizedQuery = query.toLowerCase();
    const selectedPrice = priceRanges.find((range) => range.id === price) ?? priceRanges[0];
    const result = categoryProducts.filter((product) => {
      const searchable = `${product.title} ${product.brand} ${product.subCategory} ${product.highlights.join(" ")}`.toLowerCase();
      return (
        (!normalizedQuery || searchable.includes(normalizedQuery)) &&
        (brand === "all" || product.brand === brand) &&
        product.price.sellingPrice >= selectedPrice.min &&
        product.price.sellingPrice <= selectedPrice.max &&
        (!inStockOnly || product.stock.inStock)
      );
    });

    return result.sort((a, b) => {
      if (sort === "price-asc") return a.price.sellingPrice - b.price.sellingPrice;
      if (sort === "price-desc") return b.price.sellingPrice - a.price.sellingPrice;
      if (sort === "rating") return b.rating.value - a.rating.value || b.rating.count - a.rating.count;
      if (sort === "discount") {
        return discountPercent(b.price.mrp, b.price.sellingPrice) - discountPercent(a.price.mrp, a.price.sellingPrice);
      }
      if (sort === "relevance" && normalizedQuery) return relevanceScore(b, normalizedQuery) - relevanceScore(a, normalizedQuery);
      return Number(b.badges.bestseller) - Number(a.badges.bestseller) || b.rating.count - a.rating.count;
    });
  }, [brand, categoryProducts, inStockOnly, price, query, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const visibleProducts = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const selectedCategory = category ? categoryBySlug.get(category) : undefined;
  const activeFilters = [
    brand !== "all" ? { key: "brand", label: brand } : null,
    price !== "all" ? { key: "price", label: priceRanges.find((range) => range.id === price)?.label ?? price } : null,
    inStockOnly ? { key: "stock", label: "In stock" } : null,
  ].filter((filter): filter is { key: string; label: string } => filter !== null);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [currentPage, category, query]);

  const filterControls = (
    <div className="space-y-5">
      {!category && (
        <fieldset>
          <legend className="mb-2 text-fk-md font-medium uppercase text-fk-ink">Categories</legend>
          <div className="space-y-1">
            {catalogCategories.map((item) => {
              const count = products.filter((product) => product.category === item.slug).length;
              return (
                <Link key={item.slug} to={`/category/${item.slug}`} className="flex min-h-11 items-center justify-between text-fk-base text-fk-ink hover:text-fk-blue">
                  <span>{item.shortLabel}</span>
                  <span className="text-fk-muted">{count}</span>
                </Link>
              );
            })}
          </div>
        </fieldset>
      )}

      <fieldset>
        <legend className="mb-2 text-fk-md font-medium uppercase text-fk-ink">Price</legend>
        <div className="space-y-1">
          {priceRanges.map((range) => (
            <label key={range.id} className="flex min-h-11 cursor-pointer items-center gap-2 text-fk-base text-fk-ink">
              <input type="radio" name="price" checked={price === range.id} onChange={() => updateParam("price", range.id)} className="h-4 w-4 accent-fk-blue" />
              {range.label}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="mb-2 text-fk-md font-medium uppercase text-fk-ink">Brand</legend>
        <label className="flex min-h-11 cursor-pointer items-center gap-2 text-fk-base text-fk-ink">
          <input type="radio" name="brand" checked={brand === "all"} onChange={() => updateParam("brand")} className="h-4 w-4 accent-fk-blue" />
          All brands
        </label>
        {brands.map(([name, count]) => (
          <label key={name} className="flex min-h-11 cursor-pointer items-center justify-between gap-2 text-fk-base text-fk-ink">
            <span className="flex items-center gap-2">
              <input type="radio" name="brand" checked={brand === name} onChange={() => updateParam("brand", name)} className="h-4 w-4 accent-fk-blue" />
              {name}
            </span>
            <span className="text-fk-muted">{count}</span>
          </label>
        ))}
      </fieldset>

      <label className="flex min-h-11 cursor-pointer items-center gap-2 border-t border-fk-border pt-3 text-fk-base text-fk-ink">
        <input type="checkbox" checked={inStockOnly} onChange={(event) => updateParam("stock", event.target.checked ? "in" : undefined)} className="h-4 w-4 accent-fk-blue" />
        In stock only
      </label>
    </div>
  );

  return (
    <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-[250px_1fr]">
      <aside className="sticky top-20 hidden bg-white p-5 shadow-fk-card lg:block" aria-label="Product filters">
        <div className="mb-4 flex items-center justify-between border-b border-fk-border pb-3">
          <h2 className="text-fk-lg font-medium text-fk-ink">Filters</h2>
          {activeFilters.length > 0 && <button onClick={() => setSearchParams(query ? { q: query } : {})} className="min-h-11 text-fk-sm font-medium uppercase text-fk-blue">Clear all</button>}
        </div>
        {filterControls}
      </aside>

      <section className="min-w-0 bg-white shadow-fk-card" aria-labelledby="catalog-heading">
        <header className="border-b border-fk-border px-4 py-4 sm:px-6">
          <nav aria-label="Breadcrumb" className="mb-2 text-fk-sm text-fk-muted">
            <Link to="/" className="hover:text-fk-blue">Home</Link>
            <span aria-hidden="true"> / </span>
            <span>{query ? "Search" : selectedCategory?.shortLabel ?? "All Products"}</span>
          </nav>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 id="catalog-heading" className="scroll-mt-28 text-balance text-xl font-medium text-fk-ink">
                {query ? `Search results for “${query}”` : selectedCategory?.label ?? "All Products"}
              </h1>
              <p className="mt-1 text-fk-base text-fk-muted">
                {formatIndianNumber(filtered.length)} {filtered.length === 1 ? "product" : "products"}
                {selectedCategory ? ` · ${selectedCategory.description}` : " across our complete catalog"}
              </p>
            </div>
            <label className="flex items-center gap-2 text-fk-base text-fk-muted">
              <span>Sort by</span>
              <select value={sort} onChange={(event) => updateParam("sort", event.target.value)} className="h-11 rounded-[2px] border border-fk-border bg-white px-3 text-fk-base text-fk-ink focus:border-fk-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-fk-blue" aria-label="Sort products">
                {query && <option value="relevance">Relevance</option>}
                <option value="featured">Popularity</option>
                <option value="price-asc">Price — Low to High</option>
                <option value="price-desc">Price — High to Low</option>
                <option value="rating">Customer Rating</option>
                <option value="discount">Discount</option>
              </select>
            </label>
          </div>

          <details className="mt-3 border-t border-fk-border pt-3 lg:hidden">
            <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 text-fk-md font-medium text-fk-blue">
              <SlidersHorizontal className="h-4 w-4" /> Filters {activeFilters.length > 0 ? `(${activeFilters.length})` : ""}
            </summary>
            <div className="mt-2 border-t border-fk-border pt-4">{filterControls}</div>
          </details>

          {activeFilters.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2" aria-label="Active filters">
              {activeFilters.map((filter) => (
                <button key={filter.key} onClick={() => updateParam(filter.key)} className="inline-flex min-h-9 items-center gap-1 rounded-[2px] bg-fk-bg px-3 text-fk-sm text-fk-ink hover:bg-fk-border">
                  {filter.label}<X className="h-3.5 w-3.5" />
                </button>
              ))}
            </div>
          )}
        </header>

        {visibleProducts.length > 0 ? (
          <>
            <div className="grid auto-rows-fr grid-cols-2 items-stretch gap-px bg-fk-border p-px sm:grid-cols-3 xl:grid-cols-4" data-testid="product-grid">
              {visibleProducts.map((product) => <ProductCard key={product.id} product={product} fixedWidth={false} />)}
            </div>
            {pageCount > 1 && (
              <nav className="flex items-center justify-center gap-2 border-t border-fk-border px-4 py-5" aria-label="Product pages">
                <button disabled={currentPage === 1} onClick={() => updateParam("page", String(currentPage - 1))} className="flex h-11 w-11 items-center justify-center rounded-[2px] border border-fk-border disabled:opacity-40" aria-label="Previous page"><ChevronLeft className="h-4 w-4" /></button>
                {Array.from({ length: pageCount }, (_, index) => index + 1).map((number) => (
                  <button key={number} onClick={() => updateParam("page", String(number))} aria-current={number === currentPage ? "page" : undefined} className={`h-11 min-w-11 rounded-[2px] px-3 text-fk-md ${number === currentPage ? "bg-fk-blue text-white" : "border border-fk-border bg-white text-fk-ink"}`}>{number}</button>
                ))}
                <button disabled={currentPage === pageCount} onClick={() => updateParam("page", String(currentPage + 1))} className="flex h-11 w-11 items-center justify-center rounded-[2px] border border-fk-border disabled:opacity-40" aria-label="Next page"><ChevronRight className="h-4 w-4" /></button>
              </nav>
            )}
          </>
        ) : (
          <div className="flex min-h-[440px] flex-col items-center justify-center px-6 py-16 text-center" data-testid="catalog-empty">
            <SearchX className="h-14 w-14 text-fk-muted" strokeWidth={1.5} />
            <h2 className="mt-4 text-fk-xl font-medium text-fk-ink">No products found</h2>
            <p className="mt-2 max-w-md text-fk-base text-fk-muted">Try a broader search or remove one of your filters.</p>
            <button onClick={() => setSearchParams({})} className="mt-5 min-h-11 rounded-[2px] bg-fk-blue px-6 text-fk-md font-medium uppercase text-white">Clear filters</button>
          </div>
        )}
      </section>
    </div>
  );
}
