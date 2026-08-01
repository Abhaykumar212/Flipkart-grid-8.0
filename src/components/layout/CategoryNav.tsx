import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { navCategories } from "../../data/categories";

export function CategoryNav() {
  return (
    <div className="bg-white shadow-fk-card">
      <nav className="mx-auto flex max-w-fk items-center gap-1 overflow-x-auto px-4 no-scrollbar">
        {navCategories.map((cat) => (
          <Link
            key={cat.label}
            to={`/search?category=${cat.categorySlug ?? ""}&label=${encodeURIComponent(cat.label)}`}
            className="flex shrink-0 items-center gap-1 px-4 py-3.5 text-fk-md font-medium text-fk-ink hover:text-fk-blue"
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
