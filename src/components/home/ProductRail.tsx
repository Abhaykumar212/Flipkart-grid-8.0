import { useRef } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { Product } from "../../types/product";
import { ProductCard } from "./ProductCard";

interface ProductRailProps {
  title: string;
  subtitle?: string;
  products: Product[];
}

export function ProductRail({ title, subtitle, products }: ProductRailProps) {
  const scroller = useRef<HTMLDivElement>(null);

  const scrollBy = (dir: 1 | -1) => {
    scroller.current?.scrollBy({ left: dir * 600, behavior: "smooth" });
  };

  return (
    <section className="group/rail relative mb-3 bg-white shadow-fk-card">
      <header className="flex items-center justify-between border-b border-fk-border px-6 py-4">
        <div>
          <h2 className="text-fk-xl font-medium text-fk-ink">{title}</h2>
          {subtitle && <p className="text-fk-sm text-fk-muted">{subtitle}</p>}
        </div>
        <button className="rounded-[2px] bg-fk-blue px-6 py-2.5 text-fk-md font-medium uppercase text-white">
          View All
        </button>
      </header>

      <div className="relative">
        <div
          ref={scroller}
          className="flex gap-0 overflow-x-auto scroll-smooth px-2 py-4 no-scrollbar"
        >
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>

        {/* Scroll affordances — revealed on rail hover, like Flipkart */}
        <button
          onClick={() => scrollBy(-1)}
          aria-label="Scroll left"
          className="absolute left-0 top-1/2 hidden h-16 w-9 -translate-y-1/2 items-center justify-center bg-white shadow-[2px_0_8px_rgba(0,0,0,0.2)] group-hover/rail:flex"
        >
          <ChevronLeft className="h-5 w-5 text-fk-ink" />
        </button>
        <button
          onClick={() => scrollBy(1)}
          aria-label="Scroll right"
          className="absolute right-0 top-1/2 hidden h-16 w-9 -translate-y-1/2 items-center justify-center bg-white shadow-[-2px_0_8px_rgba(0,0,0,0.2)] group-hover/rail:flex"
        >
          <ChevronRight className="h-5 w-5 text-fk-ink" />
        </button>
      </div>
    </section>
  );
}
