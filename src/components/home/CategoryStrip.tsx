import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { homeCategories } from "../../data/categories";

export function CategoryStrip() {
  return (
    <nav className="mb-3 bg-white px-3 py-3 shadow-fk-card sm:px-6" aria-label="Shop by category">
      <ul className="flex items-start justify-between gap-1 overflow-x-auto overscroll-x-contain no-scrollbar sm:gap-2">
        {homeCategories.map(({ label, icon: Icon, tint, categorySlug }) => (
          <li key={label}>
            <Link
              to={categorySlug
                ? `/category/${categorySlug}`
                : label === "All Products"
                  ? "/products"
                  : `/search?category=&label=${encodeURIComponent(label)}`}
              className="group flex w-[88px] shrink-0 flex-col items-center gap-1.5 py-1 sm:w-[104px]"
            >
              <span
                className={`flex h-14 w-14 items-center justify-center rounded-full transition-transform group-hover:scale-105 motion-reduce:transition-none sm:h-16 sm:w-16 ${tint}`}
              >
                <Icon className="h-7 w-7" strokeWidth={1.75} />
              </span>
              <span className="flex max-w-full items-center gap-0.5 truncate text-center text-fk-md font-medium text-fk-ink group-hover:text-fk-blue">
                {label}
                {categorySlug && <ChevronDown className="h-3 w-3 text-fk-muted" />}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
