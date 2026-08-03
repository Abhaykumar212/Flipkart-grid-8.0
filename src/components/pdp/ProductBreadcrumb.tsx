import { Link } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

interface ProductBreadcrumbProps {
  category: string;
  subCategory: string;
  title: string;
}

export function ProductBreadcrumb({ category, subCategory, title }: ProductBreadcrumbProps) {
  const truncatedTitle = title.length > 60 ? title.substring(0, 60) + '...' : title;

  return (
    <nav className="bg-white rounded-[2px] px-4 py-2.5 shadow-sm mb-4">
      <ul className="flex flex-wrap items-center text-fk-sm text-fk-muted">
        <li className="flex items-center">
          <Link to="/" className="text-fk-blue hover:underline flex items-center gap-1">
            <Home className="w-4 h-4" />
            Home
          </Link>
          <ChevronRight className="w-3 h-3 mx-2 opacity-50" />
        </li>
        <li className="flex items-center">
          <Link to={`/search?category=${encodeURIComponent(category)}&label=${encodeURIComponent(category)}`} className="text-fk-blue hover:underline capitalize">
            {category.replace(/-/g, ' ')}
          </Link>
          <ChevronRight className="w-3 h-3 mx-2 opacity-50" />
        </li>
        <li className="flex items-center">
          <Link to={`/search?q=${encodeURIComponent(subCategory)}`} className="text-fk-blue hover:underline capitalize">
            {subCategory.replace(/-/g, ' ')}
          </Link>
          <ChevronRight className="w-3 h-3 mx-2 opacity-50" />
        </li>
        <li className="text-fk-ink font-medium truncate" title={title}>
          {truncatedTitle}
        </li>
      </ul>
    </nav>
  );
}
