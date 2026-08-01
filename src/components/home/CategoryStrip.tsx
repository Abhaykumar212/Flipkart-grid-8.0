import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { homeCategories } from "../../data/categories";

export function CategoryStrip() {
  return (
    <nav className="mb-3 bg-white px-6 py-3 shadow-fk-card">
      <ul className="flex items-start justify-between gap-2 overflow-x-auto no-scrollbar">
        {homeCategories.map(({ label, icon: Icon, tint, categorySlug }) => (
          <li key={label}>
            <Link
              to={`/search?category=${categorySlug ?? ""}&label=${encodeURIComponent(label)}`}
              className="group flex w-[104px] shrink-0 flex-col items-center gap-1.5 py-1"
            >
              <span
                className={`flex h-16 w-16 items-center justify-center rounded-full transition-transform group-hover:scale-105 ${tint}`}
              >
                <Icon className="h-7 w-7" strokeWidth={1.75} />
              </span>
              <span className="flex items-center gap-0.5 text-center text-fk-md font-medium text-fk-ink group-hover:text-fk-blue">
                {label}
                <ChevronDown className="h-3 w-3 text-fk-muted" />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
