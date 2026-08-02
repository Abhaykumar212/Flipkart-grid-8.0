import { useRef } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { Product } from "../../types/product";
import { ProductCard } from "./ProductCard";
import { useSession } from "../../context/SessionContext";

interface ProductRailProps {
  title: string;
  subtitle?: string;
  products: Product[];
  viewAllHref?: string;
  originProductId?: string;
}

export function ProductRail({ title, subtitle, products, viewAllHref = "/products", originProductId }: ProductRailProps) {
  const scroller = useRef<HTMLDivElement>(null);
  const { emit } = useSession();

  const scrollBy = (dir: 1 | -1) => {
    scroller.current?.scrollBy({ left: dir * 600, behavior: "smooth" });
  };

  return (
    <section className="group/rail relative mb-3 overflow-hidden bg-white shadow-fk-card" aria-label={title}>
      <header className="flex min-h-18 items-center justify-between gap-4 border-b border-fk-border px-4 py-3 sm:px-6 sm:py-4">
        <div className="min-w-0">
          <h2 className="truncate text-fk-xl font-medium text-fk-ink">{title}</h2>
          {subtitle && <p className="text-fk-sm text-fk-muted">{subtitle}</p>}
        </div>
        <Link to={viewAllHref} className="inline-flex min-h-11 shrink-0 items-center rounded-[2px] bg-fk-blue px-4 py-2.5 text-fk-md font-medium uppercase text-white hover:bg-fk-blue-dark sm:px-6">
          View All
        </Link>
      </header>

      <div className="relative">
        <div
          ref={scroller}
          className="flex items-stretch gap-0 overflow-x-auto overscroll-x-contain scroll-smooth snap-x snap-mandatory px-2 py-4 no-scrollbar"
          role="region"
          aria-label={`${title} products`}
          tabIndex={0}
        >
          {products.map((p) => (
            <ProductCard
              key={p.id}
              product={p}
              onProductOpen={originProductId ? (product) => {
                emit("SIMILAR_PRODUCT_VIEWED", {
                  productId: product.id,
                  metadata: { origin_product_id: originProductId },
                });
              } : undefined}
            />
          ))}
        </div>

        {/* Scroll affordances — revealed on rail hover, like Flipkart */}
        <button
          onClick={() => scrollBy(-1)}
          aria-label="Scroll left"
          className="absolute left-0 top-1/2 hidden h-16 w-10 -translate-y-1/2 items-center justify-center bg-white shadow-[2px_0_8px_rgba(0,0,0,0.2)] lg:group-hover/rail:flex"
        >
          <ChevronLeft className="h-5 w-5 text-fk-ink" />
        </button>
        <button
          onClick={() => scrollBy(1)}
          aria-label="Scroll right"
          className="absolute right-0 top-1/2 hidden h-16 w-10 -translate-y-1/2 items-center justify-center bg-white shadow-[-2px_0_8px_rgba(0,0,0,0.2)] lg:group-hover/rail:flex"
        >
          <ChevronRight className="h-5 w-5 text-fk-ink" />
        </button>
      </div>
    </section>
  );
}
