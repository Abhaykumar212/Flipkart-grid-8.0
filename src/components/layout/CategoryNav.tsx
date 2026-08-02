import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { navCategories } from "../../data/categories";

export function CategoryNav() {
  return (
    <div className="bg-white shadow-fk-card">
      <nav className="mx-auto flex max-w-fk items-center gap-1 overflow-x-auto overscroll-x-contain px-3 no-scrollbar sm:px-4" aria-label="Product categories">
        {navCategories.map((cat) => (
          <Link
            key={cat.label}
            to={cat.categorySlug
              ? `/category/${cat.categorySlug}`
              : `/search?category=&label=${encodeURIComponent(cat.label)}`}
            className="flex min-h-12 shrink-0 items-center gap-1 px-3 text-fk-md font-medium text-fk-ink hover:text-fk-blue sm:px-4"
          >
            {cat.label}
            {cat.hasDropdown && (
              <ChevronDown className="h-3.5 w-3.5 text-fk-muted" strokeWidth={2.5} />
            )}
          </Link>
        ))}
      </nav>
    </div>
  );
}
